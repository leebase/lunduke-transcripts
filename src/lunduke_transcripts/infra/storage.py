"""SQLite and artifact persistence for pipeline state."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lunduke_transcripts.domain.models import VideoRecord


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class Storage:
    """Persistence layer for state tables and output files."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db_dir = data_dir / "db"
        self.videos_dir = data_dir / "videos"
        self.runs_dir = data_dir / "runs"
        self.db_path = self.db_dir / "lunduke_transcripts.sqlite3"
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def initialize(self) -> None:
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT,
                channel_name TEXT NOT NULL,
                channel_url TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                published_at TEXT,
                duration_seconds INTEGER,
                video_url TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transcripts (
                video_id TEXT PRIMARY KEY,
                language TEXT,
                source_type TEXT NOT NULL,
                exact_hash TEXT,
                exact_path TEXT,
                exact_text_path TEXT,
                clean_path TEXT,
                clean_model TEXT,
                clean_prompt_version TEXT,
                captured_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                filter_from TEXT,
                filter_to TEXT,
                videos_seen INTEGER DEFAULT 0,
                videos_new INTEGER DEFAULT 0,
                videos_processed INTEGER DEFAULT 0,
                videos_failed INTEGER DEFAULT 0,
                error_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS run_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                video_id TEXT,
                step TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            );
            """)
        self.conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def start_run(
        self, filter_from: datetime | None, filter_to: datetime | None
    ) -> tuple[str, datetime]:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(tz=UTC)
        self.conn.execute(
            """
            INSERT INTO runs (run_id, started_at, filter_from, filter_to)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, _iso(started_at), _iso(filter_from), _iso(filter_to)),
        )
        self.conn.commit()
        return run_id, started_at

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        videos_seen: int,
        videos_new: int,
        videos_processed: int,
        videos_failed: int,
        error_summary: str | None,
    ) -> datetime:
        finished_at = datetime.now(tz=UTC)
        self.conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, status = ?, videos_seen = ?, videos_new = ?,
                videos_processed = ?, videos_failed = ?, error_summary = ?
            WHERE run_id = ?
            """,
            (
                _iso(finished_at),
                status,
                videos_seen,
                videos_new,
                videos_processed,
                videos_failed,
                error_summary,
                run_id,
            ),
        )
        self.conn.commit()
        return finished_at

    def log_run_item(
        self,
        run_id: str,
        *,
        video_id: str | None,
        step: str,
        status: str,
        message: str | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO run_items (run_id, video_id, step, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, video_id, step, status, message),
        )
        self.conn.commit()

    def upsert_video(self, video: VideoRecord) -> None:
        now_iso = _iso(datetime.now(tz=UTC))
        self.conn.execute(
            """
            INSERT INTO videos (
                video_id, channel_id, channel_name, channel_url, title, description,
                published_at, duration_seconds, video_url, first_seen_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                channel_id=excluded.channel_id,
                channel_name=excluded.channel_name,
                channel_url=excluded.channel_url,
                title=excluded.title,
                description=COALESCE(excluded.description, videos.description),
                published_at=COALESCE(excluded.published_at, videos.published_at),
                duration_seconds=COALESCE(
                    excluded.duration_seconds, videos.duration_seconds
                ),
                video_url=excluded.video_url,
                last_seen_at=excluded.last_seen_at
            """,
            (
                video.video_id,
                video.channel_id,
                video.channel_name,
                video.channel_url,
                video.title,
                video.description,
                _iso(video.published_at),
                video.duration_seconds,
                video.video_url,
                now_iso,
                now_iso,
            ),
        )
        self.conn.commit()

    def get_video(self, video_id: str) -> VideoRecord | None:
        row = self.conn.execute(
            "SELECT * FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        if row is None:
            return None
        return VideoRecord(
            video_id=row["video_id"],
            video_url=row["video_url"],
            channel_id=row["channel_id"],
            channel_name=row["channel_name"],
            channel_url=row["channel_url"],
            title=row["title"],
            description=row["description"],
            published_at=_from_iso(row["published_at"]),
            duration_seconds=row["duration_seconds"],
        )

    def list_candidates(
        self,
        *,
        filter_from: datetime | None,
        filter_to: datetime | None,
        reprocess: bool,
    ) -> list[VideoRecord]:
        query = """
            SELECT v.*
            FROM videos v
            WHERE (? IS NULL OR v.published_at IS NULL OR v.published_at >= ?)
              AND (? IS NULL OR v.published_at IS NULL OR v.published_at <= ?)
        """
        params: list[Any] = [
            _iso(filter_from),
            _iso(filter_from),
            _iso(filter_to),
            _iso(filter_to),
        ]
        if not reprocess:
            query += (
                " AND NOT EXISTS (SELECT 1 FROM transcripts t "
                "WHERE t.video_id = v.video_id)"
            )
        query += " ORDER BY v.published_at DESC, v.video_id DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [
            VideoRecord(
                video_id=row["video_id"],
                video_url=row["video_url"],
                channel_id=row["channel_id"],
                channel_name=row["channel_name"],
                channel_url=row["channel_url"],
                title=row["title"],
                description=row["description"],
                published_at=_from_iso(row["published_at"]),
                duration_seconds=row["duration_seconds"],
            )
            for row in rows
        ]

    def write_video_metadata(
        self, video: VideoRecord, transcript_source: str, language: str | None
    ) -> Path:
        video_dir = self.videos_dir / video.video_id
        video_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = video_dir / "metadata.json"
        payload = {
            **asdict(video),
            "published_at": _iso(video.published_at),
            "captured_at": _iso(datetime.now(tz=UTC)),
            "transcript_source": transcript_source,
            "transcript_language": language,
        }
        metadata_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return metadata_path

    def write_video_artifact(self, video_id: str, filename: str, content: str) -> Path:
        video_dir = self.videos_dir / video_id
        video_dir.mkdir(parents=True, exist_ok=True)
        path = video_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def upsert_transcript(
        self,
        *,
        video_id: str,
        language: str | None,
        source_type: str,
        exact_hash: str | None,
        exact_path: Path | None,
        exact_text_path: Path | None,
        clean_path: Path | None,
        clean_model: str | None,
        clean_prompt_version: str | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO transcripts (
                video_id, language, source_type, exact_hash, exact_path,
                exact_text_path, clean_path, clean_model,
                clean_prompt_version, captured_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                language=excluded.language,
                source_type=excluded.source_type,
                exact_hash=excluded.exact_hash,
                exact_path=excluded.exact_path,
                exact_text_path=excluded.exact_text_path,
                clean_path=excluded.clean_path,
                clean_model=excluded.clean_model,
                clean_prompt_version=excluded.clean_prompt_version,
                captured_at=excluded.captured_at
            """,
            (
                video_id,
                language,
                source_type,
                exact_hash,
                str(exact_path) if exact_path else None,
                str(exact_text_path) if exact_text_path else None,
                str(clean_path) if clean_path else None,
                clean_model,
                clean_prompt_version,
                _iso(datetime.now(tz=UTC)),
            ),
        )
        self.conn.commit()

    def find_clean_text_by_hash(self, exact_hash: str) -> str | None:
        row = self.conn.execute(
            "SELECT clean_path FROM transcripts "
            "WHERE exact_hash = ? AND clean_path IS NOT NULL LIMIT 1",
            (exact_hash,),
        ).fetchone()
        if row is None:
            return None
        clean_path = Path(row["clean_path"])
        if not clean_path.exists():
            return None
        return clean_path.read_text(encoding="utf-8")

    def write_run_report(self, run_id: str) -> Path:
        run_row = self.conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        item_rows = self.conn.execute(
            "SELECT video_id, step, status, message FROM run_items "
            "WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        ).fetchall()
        payload = dict(run_row) if run_row else {"run_id": run_id}
        payload["items"] = [dict(row) for row in item_rows]
        report_path = self.runs_dir / f"{run_id}.json"
        report_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return report_path
