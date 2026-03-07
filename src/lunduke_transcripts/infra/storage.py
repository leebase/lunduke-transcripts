"""SQLite and artifact persistence for pipeline state."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
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


def _slugify_title(title: str, max_len: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not slug:
        slug = "untitled"
    return slug[:max_len].strip("-")


def _artifact_dir_name(video_id: str, title: str, published_at: datetime | None) -> str:
    date_prefix = (
        published_at.astimezone(UTC).date().isoformat()
        if published_at is not None
        else "undated"
    )
    slug = _slugify_title(title)
    return f"{date_prefix}_{slug}__{video_id}"


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
                source_kind TEXT NOT NULL DEFAULT 'youtube_video',
                channel_id TEXT,
                channel_name TEXT NOT NULL,
                channel_url TEXT NOT NULL,
                title TEXT NOT NULL,
                artifact_dir TEXT,
                description TEXT,
                published_at TEXT,
                duration_seconds INTEGER,
                video_url TEXT NOT NULL,
                local_path TEXT,
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
                transcript_json_path TEXT,
                clean_path TEXT,
                clean_model TEXT,
                clean_prompt_version TEXT,
                article_path TEXT,
                article_model TEXT,
                article_prompt_version TEXT,
                frame_manifest_path TEXT,
                tutorial_asset_bundle_path TEXT,
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
        self._ensure_column("videos", "artifact_dir", "TEXT")
        self._ensure_column(
            "videos",
            "source_kind",
            "TEXT NOT NULL DEFAULT 'youtube_video'",
        )
        self._ensure_column("videos", "local_path", "TEXT")
        self._ensure_column("transcripts", "article_path", "TEXT")
        self._ensure_column("transcripts", "article_model", "TEXT")
        self._ensure_column("transcripts", "article_prompt_version", "TEXT")
        self._ensure_column("transcripts", "transcript_json_path", "TEXT")
        self._ensure_column("transcripts", "frame_manifest_path", "TEXT")
        self._ensure_column("transcripts", "tutorial_asset_bundle_path", "TEXT")
        self._migrate_undated_artifact_dirs()
        self.conn.commit()

    def _ensure_column(
        self, table_name: str, column_name: str, column_definition: str
    ) -> None:
        rows = self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {row["name"] for row in rows}
        if column_name not in existing:
            self.conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            )

    def _migrate_undated_artifact_dirs(self) -> None:
        rows = self.conn.execute(
            "SELECT video_id, title, published_at, artifact_dir FROM videos"
        ).fetchall()
        for row in rows:
            published_at = _from_iso(row["published_at"])
            expected = _artifact_dir_name(row["video_id"], row["title"], published_at)
            current = row["artifact_dir"]
            if not current:
                self.conn.execute(
                    "UPDATE videos SET artifact_dir = ? WHERE video_id = ?",
                    (expected, row["video_id"]),
                )
                current = expected
            if current.startswith("undated_") and published_at is not None:
                self.conn.execute(
                    "UPDATE videos SET artifact_dir = ? WHERE video_id = ?",
                    (expected, row["video_id"]),
                )
                current = expected

            target_dir = self.videos_dir / current
            self._adopt_legacy_dirs(row["video_id"], target_dir)

    def _legacy_dirs_for_video(self, video_id: str, target_dir: Path) -> list[Path]:
        candidates: list[Path] = []
        video_id_dir = self.videos_dir / video_id
        if video_id_dir.exists() and video_id_dir != target_dir:
            candidates.append(video_id_dir)
        for match in sorted(self.videos_dir.glob(f"*__{video_id}")):
            if match != target_dir and match.exists():
                candidates.append(match)
        return candidates

    def _adopt_legacy_dirs(self, video_id: str, target_dir: Path) -> None:
        legacy_dirs = self._legacy_dirs_for_video(video_id, target_dir)
        for old_dir in legacy_dirs:
            if not target_dir.exists():
                old_dir.rename(target_dir)
            else:
                for child in old_dir.iterdir():
                    destination = target_dir / child.name
                    if destination.exists():
                        continue
                    child.rename(destination)
                try:
                    old_dir.rmdir()
                except OSError:
                    # Keep non-empty directories untouched if collisions
                    # left files behind.
                    pass
            self._rewrite_transcript_paths(video_id, old_dir, target_dir)

    def _rewrite_transcript_paths(
        self, video_id: str, old_dir: Path, new_dir: Path
    ) -> None:
        row = self.conn.execute(
            """
            SELECT exact_path, exact_text_path, transcript_json_path, clean_path,
                   article_path, frame_manifest_path, tutorial_asset_bundle_path
            FROM transcripts
            WHERE video_id = ?
            """,
            (video_id,),
        ).fetchone()
        if row is None:
            return

        def rewrite(value: str | None) -> str | None:
            if not value:
                return value
            old_prefix = str(old_dir) + "/"
            if value.startswith(old_prefix):
                return str(new_dir / value.removeprefix(old_prefix))
            return value

        self.conn.execute(
            """
            UPDATE transcripts
            SET exact_path = ?, exact_text_path = ?, transcript_json_path = ?,
                clean_path = ?, article_path = ?, frame_manifest_path = ?,
                tutorial_asset_bundle_path = ?
            WHERE video_id = ?
            """,
            (
                rewrite(row["exact_path"]),
                rewrite(row["exact_text_path"]),
                rewrite(row["transcript_json_path"]),
                rewrite(row["clean_path"]),
                rewrite(row["article_path"]),
                rewrite(row["frame_manifest_path"]),
                rewrite(row["tutorial_asset_bundle_path"]),
                video_id,
            ),
        )

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
        artifact_dir = _artifact_dir_name(
            video.video_id, video.title, video.published_at
        )
        self.conn.execute(
            """
            INSERT INTO videos (
                video_id, source_kind, channel_id, channel_name, channel_url, title,
                artifact_dir, description,
                published_at, duration_seconds, video_url, local_path,
                first_seen_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                source_kind=excluded.source_kind,
                channel_id=excluded.channel_id,
                channel_name=excluded.channel_name,
                channel_url=excluded.channel_url,
                title=excluded.title,
                artifact_dir=CASE
                    WHEN excluded.published_at IS NOT NULL THEN excluded.artifact_dir
                    WHEN videos.artifact_dir IS NULL THEN excluded.artifact_dir
                    ELSE videos.artifact_dir
                END,
                description=COALESCE(excluded.description, videos.description),
                published_at=COALESCE(excluded.published_at, videos.published_at),
                duration_seconds=COALESCE(
                    excluded.duration_seconds, videos.duration_seconds
                ),
                video_url=excluded.video_url,
                local_path=COALESCE(excluded.local_path, videos.local_path),
                last_seen_at=excluded.last_seen_at
            """,
            (
                video.video_id,
                video.source_kind,
                video.channel_id,
                video.channel_name,
                video.channel_url or video.video_url or video.video_id,
                video.title,
                artifact_dir,
                video.description,
                _iso(video.published_at),
                video.duration_seconds,
                video.video_url or video.video_id,
                video.local_path,
                now_iso,
                now_iso,
            ),
        )
        self.conn.commit()

    def _video_dir_for(
        self,
        video_id: str,
        title: str | None = None,
        published_at: datetime | None = None,
    ) -> Path:
        row = self.conn.execute(
            "SELECT artifact_dir, title, published_at FROM videos WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if row is None:
            resolved_title = title or video_id
            artifact_dir = _artifact_dir_name(video_id, resolved_title, published_at)
        else:
            artifact_dir = row["artifact_dir"]
            row_published = _from_iso(row["published_at"]) or published_at
            if not artifact_dir or (
                artifact_dir.startswith("undated_") and row_published is not None
            ):
                resolved_title = title or row["title"] or video_id
                resolved_published = row_published
                artifact_dir = _artifact_dir_name(
                    video_id, resolved_title, resolved_published
                )
                self.conn.execute(
                    "UPDATE videos SET artifact_dir = ? WHERE video_id = ?",
                    (artifact_dir, video_id),
                )
                self.conn.commit()

        video_dir = self.videos_dir / artifact_dir
        self._adopt_legacy_dirs(video_id, video_dir)
        return video_dir

    def get_video(self, video_id: str) -> VideoRecord | None:
        row = self.conn.execute(
            "SELECT * FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        if row is None:
            return None
        return VideoRecord(
            video_id=row["video_id"],
            title=row["title"],
            source_kind=row["source_kind"] or "youtube_video",
            video_url=row["video_url"],
            local_path=row["local_path"],
            channel_id=row["channel_id"],
            channel_name=row["channel_name"],
            channel_url=row["channel_url"],
            description=row["description"],
            published_at=_from_iso(row["published_at"]),
            duration_seconds=row["duration_seconds"],
        )

    def list_candidates(
        self,
        *,
        channel_urls: list[str] | None,
        video_ids: list[str] | None,
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
        if channel_urls:
            placeholders = ", ".join("?" for _ in channel_urls)
            query += f" AND v.channel_url IN ({placeholders})"
            params.extend(channel_urls)
        if video_ids:
            placeholders = ", ".join("?" for _ in video_ids)
            query += f" AND v.video_id IN ({placeholders})"
            params.extend(video_ids)
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
                title=row["title"],
                source_kind=row["source_kind"] or "youtube_video",
                video_url=row["video_url"],
                local_path=row["local_path"],
                channel_id=row["channel_id"],
                channel_name=row["channel_name"],
                channel_url=row["channel_url"],
                description=row["description"],
                published_at=_from_iso(row["published_at"]),
                duration_seconds=row["duration_seconds"],
            )
            for row in rows
        ]

    def write_video_metadata(
        self,
        video: VideoRecord,
        transcript_source: str,
        language: str | None,
        source_details: dict[str, str] | None = None,
    ) -> Path:
        video_dir = self._video_dir_for(
            video.video_id, title=video.title, published_at=video.published_at
        )
        video_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = video_dir / "metadata.json"
        payload = {
            **asdict(video),
            "artifact_dir": video_dir.name,
            "published_at": _iso(video.published_at),
            "captured_at": _iso(datetime.now(tz=UTC)),
            "transcript_source": transcript_source,
            "transcript_language": language,
        }
        if source_details:
            payload["transcript_source_details"] = source_details
        metadata_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return metadata_path

    def write_video_artifact(self, video_id: str, filename: str, content: str) -> Path:
        video_dir = self._video_dir_for(video_id)
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
        transcript_json_path: Path | None,
        clean_path: Path | None,
        clean_model: str | None,
        clean_prompt_version: str | None,
        article_path: Path | None,
        article_model: str | None,
        article_prompt_version: str | None,
        frame_manifest_path: Path | None,
        tutorial_asset_bundle_path: Path | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO transcripts (
                video_id, language, source_type, exact_hash, exact_path,
                exact_text_path, transcript_json_path, clean_path, clean_model,
                clean_prompt_version, article_path, article_model,
                article_prompt_version, frame_manifest_path,
                tutorial_asset_bundle_path, captured_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                language=excluded.language,
                source_type=excluded.source_type,
                exact_hash=excluded.exact_hash,
                exact_path=excluded.exact_path,
                exact_text_path=excluded.exact_text_path,
                transcript_json_path=excluded.transcript_json_path,
                clean_path=excluded.clean_path,
                clean_model=excluded.clean_model,
                clean_prompt_version=excluded.clean_prompt_version,
                article_path=excluded.article_path,
                article_model=excluded.article_model,
                article_prompt_version=excluded.article_prompt_version,
                frame_manifest_path=excluded.frame_manifest_path,
                tutorial_asset_bundle_path=excluded.tutorial_asset_bundle_path,
                captured_at=excluded.captured_at
            """,
            (
                video_id,
                language,
                source_type,
                exact_hash,
                str(exact_path) if exact_path else None,
                str(exact_text_path) if exact_text_path else None,
                str(transcript_json_path) if transcript_json_path else None,
                str(clean_path) if clean_path else None,
                clean_model,
                clean_prompt_version,
                str(article_path) if article_path else None,
                article_model,
                article_prompt_version,
                str(frame_manifest_path) if frame_manifest_path else None,
                (
                    str(tutorial_asset_bundle_path)
                    if tutorial_asset_bundle_path
                    else None
                ),
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
