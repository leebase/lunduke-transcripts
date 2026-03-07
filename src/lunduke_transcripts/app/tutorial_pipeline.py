"""Multi-agent tutorial generation pipeline."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lunduke_transcripts.app.tutorial_agent_registry import TutorialAgentRegistry
from lunduke_transcripts.domain.models import TutorialSummary
from lunduke_transcripts.infra.llm_adapter import LLMAdapter
from lunduke_transcripts.transforms.tutorial_prompts import (
    build_adversarial_review_prompt,
    build_educator_prompt,
    build_evidence_prompt,
    build_planner_prompt,
    build_system_prompt,
    build_technical_review_prompt,
    build_visual_prompt,
    build_writer_prompt,
)

AGENT_NAMES = [
    "educator",
    "tutorial-planner",
    "evidence-mapper",
    "script-writer",
    "visual-editor",
    "validator",
    "technical-reviewer",
    "adversarial-reviewer",
    "review-responder",
]

SUSPICIOUS_CODECS_PATTERN = re.compile(r"\bcodecs\b", re.IGNORECASE)
SUSPICIOUS_CODECS_CONTEXT_PATTERN = re.compile(
    r"\b(?:gpt|chatgpt|subscription|ai|tool|workflow|project|agent)\b",
    re.IGNORECASE,
)


class TutorialPipeline:
    """Generate tutorial artifacts from a canonical tutorial bundle."""

    def __init__(
        self,
        *,
        llm: LLMAdapter,
        agent_registry: TutorialAgentRegistry,
    ) -> None:
        self.llm = llm
        self.agent_registry = agent_registry

    def run(
        self,
        *,
        bundle_path: Path,
        approve_outline: bool,
        reprocess: bool = False,
        max_review_cycles: int = 1,
    ) -> TutorialSummary:
        resolved_bundle = bundle_path.expanduser().resolve()
        if not resolved_bundle.exists():
            raise RuntimeError(f"tutorial_bundle_missing: {resolved_bundle}")

        source = _load_source_bundle(resolved_bundle)
        tutorial_dir = resolved_bundle.parent / "tutorial"
        tutorial_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = tutorial_dir / "tutorial_manifest.json"

        agent_manifest = {
            name: self.agent_registry.manifest_entry(name) for name in AGENT_NAMES
        }
        inputs_signature = _sha1_json(
            {
                "bundle": source["bundle"],
                "transcript": source["transcript"],
                "frame_manifest": source["frame_manifest"],
                "agent_manifest": agent_manifest,
                "llm": {
                    "provider": self.llm.provider,
                    "model": self.llm.model,
                    "prompt_version": self.llm.prompt_version,
                },
            }
        )
        existing_manifest = _load_json(manifest_path)
        if (
            existing_manifest is not None
            and not reprocess
            and existing_manifest.get("inputs_signature") == inputs_signature
        ):
            status = str(existing_manifest.get("status", "unknown"))
            if status == "published" and approve_outline:
                return TutorialSummary(
                    status="published",
                    tutorial_dir=tutorial_dir,
                    manifest_path=manifest_path,
                    human_outline_approved=True,
                    publish_eligible=True,
                    reused_cached_outputs=True,
                )
            if status == "awaiting_outline_approval" and not approve_outline:
                return TutorialSummary(
                    status="awaiting_outline_approval",
                    tutorial_dir=tutorial_dir,
                    manifest_path=manifest_path,
                    human_outline_approved=False,
                    publish_eligible=False,
                    reused_cached_outputs=True,
                )

        reusable_outline = (
            existing_manifest is not None
            and existing_manifest.get("inputs_signature") == inputs_signature
            and existing_manifest.get("status") == "awaiting_outline_approval"
            and _all_exist(
                tutorial_dir / "tutorial_definition.json",
                tutorial_dir / "lesson_outline.json",
                tutorial_dir / "evidence_map.json",
                tutorial_dir / "frame_selection_plan.json",
            )
        )

        feedback_by_agent: dict[str, list[str]] = {}
        review_cycles = 0

        if reusable_outline:
            definition = _load_json_required(tutorial_dir / "tutorial_definition.json")
            outline = _load_json_required(tutorial_dir / "lesson_outline.json")
            evidence_map = _load_json_required(tutorial_dir / "evidence_map.json")
            frame_selection_plan = _load_json_required(
                tutorial_dir / "frame_selection_plan.json"
            )
        else:
            self._require_llm()
            definition = self._run_educator(source)
            _write_json(tutorial_dir / "tutorial_definition.json", definition)

            outline = self._run_planner(
                definition=definition,
                transcript=source["transcript"],
                feedback=[],
            )
            _write_json(tutorial_dir / "lesson_outline.json", outline)

            evidence_map = self._run_evidence_mapper(
                definition=definition,
                outline=outline,
                transcript=source["transcript"],
                feedback=[],
            )
            _write_json(tutorial_dir / "evidence_map.json", evidence_map)

            frame_selection_plan = self._run_visual_editor(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_manifest=source["frame_manifest"],
                tutorial_dir=tutorial_dir,
                feedback=[],
            )
            _write_json(
                tutorial_dir / "frame_selection_plan.json", frame_selection_plan
            )

        if not approve_outline:
            revision_plan = _build_revision_plan(
                validation_report=None, technical_report=None, adversarial_report=None
            )
            _write_json(tutorial_dir / "tutorial_revision_plan.json", revision_plan)
            manifest = _build_manifest(
                status="awaiting_outline_approval",
                tutorial_dir=tutorial_dir,
                resolved_bundle=resolved_bundle,
                inputs_signature=inputs_signature,
                agent_manifest=agent_manifest,
                human_outline_approved=False,
                publish_eligible=False,
                review_cycles=0,
                validation_report=None,
                technical_review_report=None,
                adversarial_review_report=None,
            )
            _write_json(manifest_path, manifest)
            return TutorialSummary(
                status="awaiting_outline_approval",
                tutorial_dir=tutorial_dir,
                manifest_path=manifest_path,
                human_outline_approved=False,
                publish_eligible=False,
            )

        self._require_llm()
        validation_report: dict[str, Any] | None = None
        technical_review_report: dict[str, Any] | None = None
        adversarial_review_report: dict[str, Any] | None = None
        final_failures: list[str] = []

        while True:
            draft_markdown = self._run_script_writer(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                feedback=feedback_by_agent.get("script-writer", []),
            )
            draft_markdown = _apply_public_copyedits(draft_markdown)
            (tutorial_dir / "tutorial_draft.md").write_text(
                draft_markdown, encoding="utf-8"
            )

            validation_report = _validate_tutorial(
                tutorial_dir=tutorial_dir,
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                draft_markdown=draft_markdown,
                agent_manifest=agent_manifest,
            )
            _write_json(
                tutorial_dir / "tutorial_validation_report.json", validation_report
            )

            technical_review_report = self._run_technical_review(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                draft_markdown=draft_markdown,
                validation_report=validation_report,
            )
            adversarial_review_report = self._run_adversarial_review(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                draft_markdown=draft_markdown,
                validation_report=validation_report,
            )

            _write_json(
                tutorial_dir / "technical_review_report.json",
                technical_review_report,
            )
            _write_json(
                tutorial_dir / "adversarial_review_report.json",
                adversarial_review_report,
            )

            revision_plan = _build_revision_plan(
                validation_report=validation_report,
                technical_report=technical_review_report,
                adversarial_report=adversarial_review_report,
            )
            _write_json(tutorial_dir / "tutorial_revision_plan.json", revision_plan)

            validation_attention_required = _report_attention_required(
                validation_report
            )
            technical_attention_required = _report_attention_required(
                technical_review_report
            )
            adversarial_attention_required = _report_attention_required(
                adversarial_review_report
            )
            editorial_attention_required = bool(
                validation_attention_required
                or technical_attention_required
                or adversarial_attention_required
            )
            if not editorial_attention_required:
                final_path = tutorial_dir / "tutorial_final.md"
                final_path.write_text(draft_markdown, encoding="utf-8")
                manifest = _build_manifest(
                    status="published",
                    tutorial_dir=tutorial_dir,
                    resolved_bundle=resolved_bundle,
                    inputs_signature=inputs_signature,
                    agent_manifest=agent_manifest,
                    human_outline_approved=True,
                    publish_eligible=True,
                    review_cycles=review_cycles,
                    validation_report=validation_report,
                    technical_review_report=technical_review_report,
                    adversarial_review_report=adversarial_review_report,
                )
                _write_json(manifest_path, manifest)
                return TutorialSummary(
                    status="published",
                    tutorial_dir=tutorial_dir,
                    manifest_path=manifest_path,
                    human_outline_approved=True,
                    publish_eligible=True,
                    review_cycles=review_cycles,
                )

            if review_cycles >= max_review_cycles:
                final_path = tutorial_dir / "tutorial_final.md"
                final_path.write_text(draft_markdown, encoding="utf-8")
                final_failures = _collect_failure_messages(
                    validation_report,
                    technical_review_report,
                    adversarial_review_report,
                )
                manifest = _build_manifest(
                    status="published",
                    tutorial_dir=tutorial_dir,
                    resolved_bundle=resolved_bundle,
                    inputs_signature=inputs_signature,
                    agent_manifest=agent_manifest,
                    human_outline_approved=True,
                    publish_eligible=True,
                    review_cycles=review_cycles,
                    validation_report=validation_report,
                    technical_review_report=technical_review_report,
                    adversarial_review_report=adversarial_review_report,
                )
                _write_json(manifest_path, manifest)
                return TutorialSummary(
                    status="published",
                    tutorial_dir=tutorial_dir,
                    manifest_path=manifest_path,
                    human_outline_approved=True,
                    publish_eligible=True,
                    review_cycles=review_cycles,
                    failures=final_failures,
                )

            review_cycles += 1
            feedback_by_agent = revision_plan["feedback_by_agent"]
            rerun_from_stage = revision_plan["rerun_from_stage"]

            if rerun_from_stage == "educator":
                definition = self._run_educator(
                    source,
                    feedback=feedback_by_agent.get("educator", []),
                )
                _write_json(tutorial_dir / "tutorial_definition.json", definition)
                outline = self._run_planner(
                    definition=definition,
                    transcript=source["transcript"],
                    feedback=feedback_by_agent.get("tutorial-planner", []),
                )
                _write_json(tutorial_dir / "lesson_outline.json", outline)
                evidence_map = self._run_evidence_mapper(
                    definition=definition,
                    outline=outline,
                    transcript=source["transcript"],
                    feedback=feedback_by_agent.get("evidence-mapper", []),
                )
                _write_json(tutorial_dir / "evidence_map.json", evidence_map)
                frame_selection_plan = self._run_visual_editor(
                    definition=definition,
                    outline=outline,
                    evidence_map=evidence_map,
                    frame_manifest=source["frame_manifest"],
                    tutorial_dir=tutorial_dir,
                    feedback=feedback_by_agent.get("visual-editor", []),
                )
                _write_json(
                    tutorial_dir / "frame_selection_plan.json",
                    frame_selection_plan,
                )
                continue

            if rerun_from_stage == "tutorial-planner":
                outline = self._run_planner(
                    definition=definition,
                    transcript=source["transcript"],
                    feedback=feedback_by_agent.get("tutorial-planner", []),
                )
                _write_json(tutorial_dir / "lesson_outline.json", outline)
                evidence_map = self._run_evidence_mapper(
                    definition=definition,
                    outline=outline,
                    transcript=source["transcript"],
                    feedback=feedback_by_agent.get("evidence-mapper", []),
                )
                _write_json(tutorial_dir / "evidence_map.json", evidence_map)
                frame_selection_plan = self._run_visual_editor(
                    definition=definition,
                    outline=outline,
                    evidence_map=evidence_map,
                    frame_manifest=source["frame_manifest"],
                    tutorial_dir=tutorial_dir,
                    feedback=feedback_by_agent.get("visual-editor", []),
                )
                _write_json(
                    tutorial_dir / "frame_selection_plan.json",
                    frame_selection_plan,
                )
                continue

            if rerun_from_stage == "evidence-mapper":
                evidence_map = self._run_evidence_mapper(
                    definition=definition,
                    outline=outline,
                    transcript=source["transcript"],
                    feedback=feedback_by_agent.get("evidence-mapper", []),
                )
                _write_json(tutorial_dir / "evidence_map.json", evidence_map)
                frame_selection_plan = self._run_visual_editor(
                    definition=definition,
                    outline=outline,
                    evidence_map=evidence_map,
                    frame_manifest=source["frame_manifest"],
                    tutorial_dir=tutorial_dir,
                    feedback=feedback_by_agent.get("visual-editor", []),
                )
                _write_json(
                    tutorial_dir / "frame_selection_plan.json",
                    frame_selection_plan,
                )
                continue

            if rerun_from_stage == "visual-editor":
                frame_selection_plan = self._run_visual_editor(
                    definition=definition,
                    outline=outline,
                    evidence_map=evidence_map,
                    frame_manifest=source["frame_manifest"],
                    tutorial_dir=tutorial_dir,
                    feedback=feedback_by_agent.get("visual-editor", []),
                )
                _write_json(
                    tutorial_dir / "frame_selection_plan.json",
                    frame_selection_plan,
                )
                continue

            if rerun_from_stage == "script-writer":
                continue

            raise RuntimeError(
                f"unsupported_tutorial_reroute_stage: {rerun_from_stage}"
            )

    def _require_llm(self) -> None:
        if not self.llm.is_enabled():
            raise RuntimeError("tutorial_generation_requires_llm_configuration")

    def _run_educator(
        self,
        source: dict[str, Any],
        *,
        feedback: list[str] | None = None,
    ) -> dict[str, Any]:
        agent = self.agent_registry.load("educator")
        prompt = build_educator_prompt(
            bundle=source["bundle"],
            transcript=source["transcript"],
            frame_manifest=source["frame_manifest"],
        )
        if feedback:
            prompt += "\nReview feedback:\n" + "\n".join(
                f"- {item}" for item in feedback
            )
        payload, _, _ = self.llm.run_json_task(
            task_name="tutorial.educator",
            system_prompt=build_system_prompt(agent),
            user_prompt=prompt,
        )
        return _normalize_definition(payload)

    def _run_planner(
        self,
        *,
        definition: dict[str, Any],
        transcript: dict[str, Any],
        feedback: list[str],
    ) -> dict[str, Any]:
        agent = self.agent_registry.load("tutorial-planner")
        payload, _, _ = self.llm.run_json_task(
            task_name="tutorial.planner",
            system_prompt=build_system_prompt(agent),
            user_prompt=build_planner_prompt(
                definition=definition,
                transcript=transcript,
                feedback=feedback,
            ),
        )
        return _normalize_outline(payload)

    def _run_evidence_mapper(
        self,
        *,
        definition: dict[str, Any],
        outline: dict[str, Any],
        transcript: dict[str, Any],
        feedback: list[str],
    ) -> dict[str, Any]:
        agent = self.agent_registry.load("evidence-mapper")
        payload, _, _ = self.llm.run_json_task(
            task_name="tutorial.evidence",
            system_prompt=build_system_prompt(agent),
            user_prompt=build_evidence_prompt(
                definition=definition,
                outline=outline,
                transcript=transcript,
                feedback=feedback,
            ),
        )
        return _normalize_evidence_map(payload, outline)

    def _run_visual_editor(
        self,
        *,
        definition: dict[str, Any],
        outline: dict[str, Any],
        evidence_map: dict[str, Any],
        frame_manifest: dict[str, Any] | None,
        tutorial_dir: Path,
        feedback: list[str],
    ) -> dict[str, Any]:
        agent = self.agent_registry.load("visual-editor")
        payload, _, _ = self.llm.run_json_task(
            task_name="tutorial.visual",
            system_prompt=build_system_prompt(agent),
            user_prompt=build_visual_prompt(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_manifest=frame_manifest,
                tutorial_dir=tutorial_dir,
                feedback=feedback,
            ),
        )
        return _normalize_frame_selection_plan(payload, outline, frame_manifest)

    def _run_script_writer(
        self,
        *,
        definition: dict[str, Any],
        outline: dict[str, Any],
        evidence_map: dict[str, Any],
        frame_selection_plan: dict[str, Any],
        feedback: list[str],
    ) -> str:
        agent = self.agent_registry.load("script-writer")
        text, _, _ = self.llm.run_text_task(
            task_name="tutorial.writer",
            system_prompt=build_system_prompt(agent),
            user_prompt=build_writer_prompt(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                review_feedback=feedback,
            ),
        )
        return text.strip() + "\n"

    def _run_technical_review(
        self,
        *,
        definition: dict[str, Any],
        outline: dict[str, Any],
        evidence_map: dict[str, Any],
        frame_selection_plan: dict[str, Any],
        draft_markdown: str,
        validation_report: dict[str, Any],
    ) -> dict[str, Any]:
        agent = self.agent_registry.load("technical-reviewer")
        payload, _, _ = self.llm.run_json_task(
            task_name="tutorial.technical-review",
            system_prompt=build_system_prompt(agent),
            user_prompt=build_technical_review_prompt(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                draft_markdown=draft_markdown,
                validation_report=validation_report,
            ),
        )
        return _normalize_review_report(payload, "technical-reviewer")

    def _run_adversarial_review(
        self,
        *,
        definition: dict[str, Any],
        outline: dict[str, Any],
        evidence_map: dict[str, Any],
        frame_selection_plan: dict[str, Any],
        draft_markdown: str,
        validation_report: dict[str, Any],
    ) -> dict[str, Any]:
        agent = self.agent_registry.load("adversarial-reviewer")
        payload, _, _ = self.llm.run_json_task(
            task_name="tutorial.adversarial-review",
            system_prompt=build_system_prompt(agent),
            user_prompt=build_adversarial_review_prompt(
                definition=definition,
                outline=outline,
                evidence_map=evidence_map,
                frame_selection_plan=frame_selection_plan,
                draft_markdown=draft_markdown,
                validation_report=validation_report,
            ),
        )
        return _normalize_adversarial_review_report(payload)


def _load_source_bundle(bundle_path: Path) -> dict[str, Any]:
    bundle = _load_json_required(bundle_path)
    transcript_path = _resolve_artifact_path(bundle_path, bundle.get("transcript_path"))
    if transcript_path is None:
        raise RuntimeError("tutorial_bundle_missing_transcript_path")
    transcript = _load_json_required(transcript_path)
    frame_manifest_path = _resolve_artifact_path(
        bundle_path,
        bundle.get("frame_manifest_path"),
    )
    frame_manifest = _load_json(frame_manifest_path) if frame_manifest_path else None
    metadata_path = _resolve_artifact_path(bundle_path, bundle.get("metadata_path"))
    metadata = _load_json(metadata_path) if metadata_path else None
    return {
        "bundle": bundle,
        "transcript": transcript,
        "frame_manifest": frame_manifest,
        "metadata": metadata,
    }


def _resolve_artifact_path(bundle_path: Path, relative_path: object) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path.strip():
        return None
    return (bundle_path.parent / relative_path).resolve()


def _validate_tutorial(
    *,
    tutorial_dir: Path,
    definition: dict[str, Any],
    outline: dict[str, Any],
    evidence_map: dict[str, Any],
    frame_selection_plan: dict[str, Any],
    draft_markdown: str,
    agent_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    structure_findings = _validate_public_tutorial_markdown(
        draft_markdown,
        definition,
    )
    findings.extend(structure_findings)
    evidence_steps = {
        entry["step_id"]: entry for entry in evidence_map.get("steps", [])
    }
    frame_steps = {
        entry["step_id"]: entry for entry in frame_selection_plan.get("steps", [])
    }
    all_step_ids: list[str] = []
    for section in outline.get("sections", []):
        for step in section.get("steps", []):
            step_id = step.get("step_id")
            if not step_id:
                continue
            all_step_ids.append(step_id)
            evidence = evidence_steps.get(step_id)
            if not evidence or not evidence.get("segment_indexes"):
                findings.append(
                    _finding(
                        severity="blocking",
                        category="missing_evidence",
                        message="Step is missing transcript evidence.",
                        step_id=step_id,
                        reroute_target="evidence-mapper",
                    )
                )
            frame = frame_steps.get(step_id)
            if frame is None:
                findings.append(
                    _finding(
                        severity="blocking",
                        category="missing_frame_selection",
                        message="Step is missing visual selection metadata.",
                        step_id=step_id,
                        reroute_target="visual-editor",
                    )
                )
                continue
            if frame.get("selected_frame_path"):
                image_path = (
                    tutorial_dir.parent / frame["selected_frame_path"]
                ).resolve()
                if not image_path.exists():
                    findings.append(
                        _finding(
                            severity="blocking",
                            category="missing_frame_file",
                            message="Selected frame file does not exist on disk.",
                            step_id=step_id,
                            reroute_target="visual-editor",
                        )
                    )
            elif frame.get("text_only"):
                if not str(frame.get("text_only_reason") or "").strip():
                    findings.append(
                        _finding(
                            severity="blocking",
                            category="missing_text_only_justification",
                            message="Text-only step is missing a justification.",
                            step_id=step_id,
                            reroute_target="visual-editor",
                        )
                    )
            else:
                findings.append(
                    _finding(
                        severity="blocking",
                        category="weak_visual_support",
                        message="Step has no frame and is not marked text-only.",
                        step_id=step_id,
                        reroute_target="visual-editor",
                    )
                )
            if step.get("title") and step["title"] not in draft_markdown:
                findings.append(
                    _finding(
                        severity="medium",
                        category="draft_structure",
                        message="Step title is not clearly represented in the draft.",
                        step_id=step_id,
                        reroute_target="script-writer",
                    )
                )
    if not agent_manifest:
        findings.append(
            _finding(
                severity="blocking",
                category="metadata",
                message="Agent metadata is missing from validation context.",
                step_id=None,
                reroute_target="script-writer",
            )
        )
    return {
        "schema_version": "1",
        "validated_at": datetime.now(tz=UTC).isoformat(),
        "step_count": len(all_step_ids),
        "attention_required": any(findings),
        "overall_blocked": any(
            finding["severity"] == "blocking" for finding in findings
        ),
        "findings": findings,
    }


def _validate_public_tutorial_markdown(
    draft_markdown: str,
    definition: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    requires_context = bool(definition.get("context_section_required", True))
    requires_toc = bool(definition.get("table_of_contents_required", True))
    requires_back_to_top = bool(definition.get("back_to_top_links_required", True))

    if requires_back_to_top and '<a id="top"></a>' not in draft_markdown:
        findings.append(
            _finding(
                severity="blocking",
                category="missing_top_anchor",
                message="Final tutorial is missing the required top anchor.",
                step_id=None,
                reroute_target="script-writer",
            )
        )
    if requires_context and "## What This Tutorial Is For" not in draft_markdown:
        findings.append(
            _finding(
                severity="blocking",
                category="missing_context_section",
                message="Final tutorial is missing the required context section.",
                step_id=None,
                reroute_target="script-writer",
            )
        )
    if requires_toc and "## Table of Contents" not in draft_markdown:
        findings.append(
            _finding(
                severity="blocking",
                category="missing_table_of_contents",
                message="Final tutorial is missing the required table of contents.",
                step_id=None,
                reroute_target="script-writer",
            )
        )
    if requires_back_to_top:
        sections_requiring_navigation = _sections_requiring_back_to_top(
            draft_markdown,
            requires_toc=requires_toc,
        )
        if not sections_requiring_navigation:
            findings.append(
                _finding(
                    severity="blocking",
                    category="missing_back_to_top_links",
                    message=(
                        "Final tutorial is missing major sections that can "
                        "carry back-to-top navigation."
                    ),
                    step_id=None,
                    reroute_target="script-writer",
                )
            )
        else:
            for section_title, section_body in sections_requiring_navigation:
                if "[Back to top](#top)" not in section_body:
                    findings.append(
                        _finding(
                            severity="blocking",
                            category="missing_back_to_top_links",
                            message=(
                                "Section is missing the required back-to-top "
                                f"link: {section_title}."
                            ),
                            step_id=None,
                            reroute_target="script-writer",
                        )
                    )
    if re.search(r"(^|\n)\s*>\s*\*\*Evidence:", draft_markdown):
        findings.append(
            _finding(
                severity="blocking",
                category="evidence_leakage",
                message=(
                    "Final tutorial leaks internal evidence callouts into "
                    "the public artifact."
                ),
                step_id=None,
                reroute_target="script-writer",
            )
        )
    if re.search(r"\bEvidence:\b", draft_markdown):
        findings.append(
            _finding(
                severity="blocking",
                category="evidence_leakage",
                message=(
                    "Final tutorial contains raw evidence labeling that "
                    "should stay in sidecar artifacts."
                ),
                step_id=None,
                reroute_target="script-writer",
            )
        )
    if re.search(r"\bthe speaker\b", draft_markdown, re.IGNORECASE):
        findings.append(
            _finding(
                severity="medium",
                category="transcript_leakage",
                message=(
                    "Final tutorial still narrates the source instead of "
                    "teaching the workflow directly."
                ),
                step_id=None,
                reroute_target="script-writer",
            )
        )
    if _contains_suspicious_codex_confusion(draft_markdown):
        findings.append(
            _finding(
                severity="medium",
                category="terminology",
                message=(
                    "Use `Codex`, not `codecs`, when referring to the AI tool name."
                ),
                step_id=None,
                reroute_target="script-writer",
            )
        )
    return findings


def _contains_suspicious_codex_confusion(draft_markdown: str) -> bool:
    normalized_markdown = draft_markdown.replace("Codex", "")
    for match in SUSPICIOUS_CODECS_PATTERN.finditer(normalized_markdown):
        start = max(match.start() - 80, 0)
        end = min(match.end() + 80, len(normalized_markdown))
        context_window = normalized_markdown[start:end]
        if SUSPICIOUS_CODECS_CONTEXT_PATTERN.search(context_window):
            return True
    return False


def _apply_public_copyedits(draft_markdown: str) -> str:
    if "Codex" in draft_markdown or _contains_suspicious_codex_confusion(
        draft_markdown
    ):
        return SUSPICIOUS_CODECS_PATTERN.sub("Codex", draft_markdown)

    pieces: list[str] = []
    last_index = 0
    for match in SUSPICIOUS_CODECS_PATTERN.finditer(draft_markdown):
        pieces.append(draft_markdown[last_index : match.start()])
        replacement = match.group(0)
        start = max(match.start() - 80, 0)
        end = min(match.end() + 80, len(draft_markdown))
        context_window = draft_markdown[start:end]
        if SUSPICIOUS_CODECS_CONTEXT_PATTERN.search(context_window):
            replacement = "Codex"
        pieces.append(replacement)
        last_index = match.end()

    if not pieces:
        return draft_markdown

    pieces.append(draft_markdown[last_index:])
    return "".join(pieces)


def _sections_requiring_back_to_top(
    draft_markdown: str,
    *,
    requires_toc: bool,
) -> list[tuple[str, str]]:
    heading_matches = list(re.finditer(r"(?m)^##\s+(.+)$", draft_markdown))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(heading_matches):
        title = match.group(1).strip()
        start = match.start()
        end = (
            heading_matches[index + 1].start()
            if index + 1 < len(heading_matches)
            else len(draft_markdown)
        )
        sections.append((title, draft_markdown[start:end]))

    if not sections:
        return []

    if requires_toc:
        for index, (title, _) in enumerate(sections):
            if title.lower() == "table of contents":
                return sections[index + 1 :]

    return sections[1:]


def _build_revision_plan(
    *,
    validation_report: dict[str, Any] | None,
    technical_report: dict[str, Any] | None,
    adversarial_report: dict[str, Any] | None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for report in (validation_report, technical_report, adversarial_report):
        if report:
            findings.extend(report.get("findings", []))
    by_target: dict[str, list[str]] = {}
    for finding in findings:
        target = str(finding.get("reroute_target") or "script-writer")
        by_target.setdefault(target, []).append(
            str(finding.get("message") or "").strip()
        )

    rerun_from_stage = "script-writer"
    if any(target == "educator" for target in by_target):
        rerun_from_stage = "educator"
    elif any(target == "tutorial-planner" for target in by_target):
        rerun_from_stage = "tutorial-planner"
    elif any(target == "evidence-mapper" for target in by_target):
        rerun_from_stage = "evidence-mapper"
    elif any(target == "visual-editor" for target in by_target):
        rerun_from_stage = "visual-editor"

    editorial_attention_required = any(
        _report_attention_required(report)
        for report in (validation_report, technical_report, adversarial_report)
    )
    return {
        "schema_version": "1",
        "overall_blocked": False,
        "editorial_attention_required": editorial_attention_required,
        "adversarial_attention_required": bool(
            adversarial_report and adversarial_report.get("attention_required")
        ),
        "rerun_from_stage": rerun_from_stage,
        "feedback_by_agent": by_target,
        "findings_considered": findings,
    }


def _build_manifest(
    *,
    status: str,
    tutorial_dir: Path,
    resolved_bundle: Path,
    inputs_signature: str,
    agent_manifest: dict[str, Any],
    human_outline_approved: bool,
    publish_eligible: bool,
    review_cycles: int,
    validation_report: dict[str, Any] | None,
    technical_review_report: dict[str, Any] | None,
    adversarial_review_report: dict[str, Any] | None,
) -> dict[str, Any]:
    validation_attention_required = _report_attention_required(validation_report)
    technical_attention_required = _report_attention_required(technical_review_report)
    adversarial_attention_required = _report_attention_required(
        adversarial_review_report
    )
    return {
        "schema_version": "1",
        "status": status,
        "source_bundle_path": str(resolved_bundle),
        "inputs_signature": inputs_signature,
        "human_outline_approved": human_outline_approved,
        "publish_eligible": publish_eligible,
        "review_cycles": review_cycles,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "artifacts": {
            "tutorial_definition": _artifact_entry(
                tutorial_dir / "tutorial_definition.json"
            ),
            "lesson_outline": _artifact_entry(tutorial_dir / "lesson_outline.json"),
            "evidence_map": _artifact_entry(tutorial_dir / "evidence_map.json"),
            "frame_selection_plan": _artifact_entry(
                tutorial_dir / "frame_selection_plan.json"
            ),
            "tutorial_draft": _artifact_entry(tutorial_dir / "tutorial_draft.md"),
            "tutorial_validation_report": _artifact_entry(
                tutorial_dir / "tutorial_validation_report.json"
            ),
            "technical_review_report": _artifact_entry(
                tutorial_dir / "technical_review_report.json"
            ),
            "adversarial_review_report": _artifact_entry(
                tutorial_dir / "adversarial_review_report.json"
            ),
            "tutorial_revision_plan": _artifact_entry(
                tutorial_dir / "tutorial_revision_plan.json"
            ),
            "tutorial_final": _artifact_entry(tutorial_dir / "tutorial_final.md"),
        },
        "agents": agent_manifest,
        "review_outcomes": {
            "validation_blocked": False,
            "technical_blocked": False,
            "adversarial_blocked": False,
            "adversarial_gate_mode": "advisory",
            "validation_attention_required": validation_attention_required,
            "technical_attention_required": technical_attention_required,
            "adversarial_attention_required": adversarial_attention_required,
            "editorial_attention_required": bool(
                validation_attention_required
                or technical_attention_required
                or adversarial_attention_required
            ),
            "validation_findings": len(
                validation_report.get("findings", []) if validation_report else []
            ),
            "technical_findings": len(
                technical_review_report.get("findings", [])
                if technical_review_report
                else []
            ),
            "adversarial_unresolved_findings": len(
                adversarial_review_report.get("findings", [])
                if adversarial_review_report
                else []
            ),
            "adversarial_scores": (
                {
                    "source_fidelity_score": adversarial_review_report.get(
                        "source_fidelity_score"
                    ),
                    "teachability_score": adversarial_review_report.get(
                        "teachability_score"
                    ),
                    "visual_support_score": adversarial_review_report.get(
                        "visual_support_score"
                    ),
                }
                if adversarial_review_report
                else None
            ),
        },
    }


def _artifact_entry(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
    }


def _normalize_definition(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "target_audience": str(payload.get("target_audience") or "technical_user"),
        "learning_objectives": _string_list(payload.get("learning_objectives")),
        "prerequisites": _string_list(payload.get("prerequisites")),
        "success_criteria": _string_list(payload.get("success_criteria")),
        "allowed_enrichment_level": str(
            payload.get("allowed_enrichment_level") or "light"
        ),
        "evidence_requirements": deepcopy(payload.get("evidence_requirements") or {}),
        "visual_requirements": deepcopy(payload.get("visual_requirements") or {}),
        "blocking_conditions": _string_list(payload.get("blocking_conditions")),
        "output_targets": _string_list(payload.get("output_targets")) or ["markdown"],
        "context_section_required": bool(payload.get("context_section_required", True)),
        "table_of_contents_required": bool(
            payload.get("table_of_contents_required", True)
        ),
        "back_to_top_links_required": bool(
            payload.get("back_to_top_links_required", True)
        ),
    }


def _normalize_outline(payload: dict[str, Any]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raw_sections = []
    for section_index, raw_section in enumerate(raw_sections, start=1):
        if not isinstance(raw_section, dict):
            continue
        raw_steps = raw_section.get("steps")
        steps: list[dict[str, Any]] = []
        if isinstance(raw_steps, list):
            for step_index, raw_step in enumerate(raw_steps, start=1):
                if not isinstance(raw_step, dict):
                    continue
                steps.append(
                    {
                        "step_id": str(
                            raw_step.get("step_id")
                            or f"section-{section_index}-step-{step_index}"
                        ),
                        "title": str(raw_step.get("title") or f"Step {step_index}"),
                        "instruction": str(raw_step.get("instruction") or ""),
                        "assumptions": _string_list(raw_step.get("assumptions")),
                        "text_only_allowed": bool(raw_step.get("text_only_allowed")),
                    }
                )
        sections.append(
            {
                "section_id": str(
                    raw_section.get("section_id") or f"section-{section_index}"
                ),
                "title": str(raw_section.get("title") or f"Section {section_index}"),
                "goal": str(raw_section.get("goal") or ""),
                "steps": steps,
            }
        )
    return {"schema_version": "1", "sections": sections}


def _normalize_evidence_map(
    payload: dict[str, Any],
    outline: dict[str, Any],
) -> dict[str, Any]:
    by_step = {
        str(item.get("step_id")): item
        for item in payload.get("steps", [])
        if isinstance(item, dict) and item.get("step_id")
    }
    steps: list[dict[str, Any]] = []
    for section in outline.get("sections", []):
        for step in section.get("steps", []):
            raw = by_step.get(step["step_id"], {})
            steps.append(
                {
                    "step_id": step["step_id"],
                    "segment_indexes": [
                        int(index)
                        for index in raw.get("segment_indexes", [])
                        if isinstance(index, int)
                    ],
                    "evidence_strength": str(
                        raw.get("evidence_strength") or "weak"
                    ).lower(),
                    "supporting_quote": str(raw.get("supporting_quote") or ""),
                    "assumptions": _string_list(raw.get("assumptions")),
                    "notes": str(raw.get("notes") or ""),
                }
            )
    return {"schema_version": "1", "steps": steps}


def _normalize_frame_selection_plan(
    payload: dict[str, Any],
    outline: dict[str, Any],
    frame_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    available_paths = {
        str(frame.get("image_path"))
        for frame in (frame_manifest or {}).get("frames", [])
        if isinstance(frame, dict) and frame.get("image_path")
    }
    by_step = {
        str(item.get("step_id")): item
        for item in payload.get("steps", [])
        if isinstance(item, dict) and item.get("step_id")
    }
    steps: list[dict[str, Any]] = []
    for section in outline.get("sections", []):
        for step in section.get("steps", []):
            raw = by_step.get(step["step_id"], {})
            selected_frame_path = (
                str(raw.get("selected_frame_path") or "").strip() or None
            )
            if selected_frame_path and selected_frame_path not in available_paths:
                selected_frame_path = None
            text_only = bool(raw.get("text_only"))
            if selected_frame_path:
                text_only = False
            markdown_image_path = (
                (Path("..") / selected_frame_path).as_posix()
                if selected_frame_path
                else None
            )
            steps.append(
                {
                    "step_id": step["step_id"],
                    "selected_frame_path": selected_frame_path,
                    "markdown_image_path": markdown_image_path,
                    "caption": str(raw.get("caption") or ""),
                    "alt_text": str(raw.get("alt_text") or ""),
                    "support_strength": str(raw.get("support_strength") or "weak"),
                    "text_only": text_only,
                    "text_only_reason": (
                        str(raw.get("text_only_reason") or "") if text_only else None
                    ),
                    "notes": str(raw.get("notes") or ""),
                }
            )
    return {"schema_version": "1", "steps": steps}


def _normalize_review_report(
    payload: dict[str, Any], agent_name: str
) -> dict[str, Any]:
    findings = [_normalize_finding(item) for item in payload.get("findings", [])]
    attention_required = bool(
        payload.get("attention_required") or payload.get("overall_blocked")
    )
    if any(finding["severity"] in {"high", "blocking"} for finding in findings):
        attention_required = True
    return {
        "schema_version": "1",
        "agent": agent_name,
        "overall_blocked": bool(payload.get("overall_blocked")),
        "attention_required": attention_required,
        "advisory_only": True,
        "findings": findings,
    }


def _normalize_adversarial_review_report(payload: dict[str, Any]) -> dict[str, Any]:
    findings = [_normalize_finding(item) for item in payload.get("findings", [])]
    source_fidelity_score = _clamp_score(payload.get("source_fidelity_score"))
    teachability_score = _clamp_score(payload.get("teachability_score"))
    visual_support_score = _clamp_score(payload.get("visual_support_score"))
    attention_required = bool(payload.get("attention_required")) or any(
        finding["severity"] == "high" for finding in findings
    )
    if any(finding["category"] == "source_fidelity" for finding in findings):
        attention_required = True
    return {
        "schema_version": "1",
        "agent": "adversarial-reviewer",
        "source_fidelity_score": source_fidelity_score,
        "teachability_score": teachability_score,
        "visual_support_score": visual_support_score,
        "overall_blocked": False,
        "advisory_only": True,
        "attention_required": attention_required,
        "counter_narrative_summary": str(
            payload.get("counter_narrative_summary") or ""
        ),
        "recommended_reroute": str(
            payload.get("recommended_reroute") or "script-writer"
        ),
        "skills_used": [
            "source-grounding-attack",
            "learner-confusion-attack",
        ],
        "findings": findings,
    }


def _normalize_finding(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _finding(
            severity="medium",
            category="unknown",
            message=str(value),
            step_id=None,
            reroute_target="script-writer",
        )
    severity = str(value.get("severity") or "medium").lower()
    if severity not in {"low", "medium", "high", "blocking"}:
        severity = "medium"
    if severity == "blocking":
        severity = "high"
    return _finding(
        severity=severity,
        category=str(value.get("category") or "unknown"),
        message=str(value.get("message") or ""),
        step_id=(str(value["step_id"]) if value.get("step_id") else None),
        reroute_target=str(value.get("reroute_target") or "script-writer"),
    )


def _finding(
    *,
    severity: str,
    category: str,
    message: str,
    step_id: str | None,
    reroute_target: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "step_id": step_id,
        "reroute_target": reroute_target,
    }


def _skipped_review_report(agent_name: str, reason: str) -> dict[str, Any]:
    payload = {
        "schema_version": "1",
        "agent": agent_name,
        "overall_blocked": False,
        "skipped": True,
        "skip_reason": reason,
        "findings": [],
    }
    if agent_name == "adversarial-reviewer":
        payload.update(
            {
                "source_fidelity_score": 0.0,
                "teachability_score": 0.0,
                "visual_support_score": 0.0,
                "attention_required": False,
                "advisory_only": True,
                "counter_narrative_summary": "",
                "recommended_reroute": "visual-editor",
                "skills_used": [
                    "source-grounding-attack",
                    "learner-confusion-attack",
                ],
            }
        )
    return payload


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_required(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if payload is None:
        raise RuntimeError(f"missing_required_json_artifact: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _all_exist(*paths: Path) -> bool:
    return all(path.exists() for path in paths)


def _collect_failure_messages(*reports: dict[str, Any] | None) -> list[str]:
    messages: list[str] = []
    for report in reports:
        if not report:
            continue
        for finding in report.get("findings", []):
            message = str(finding.get("message") or "").strip()
            if message:
                messages.append(message)
    return messages


def _collect_advisory_messages(
    adversarial_report: dict[str, Any] | None,
) -> list[str]:
    if not adversarial_report:
        return []
    messages: list[str] = []
    for finding in adversarial_report.get("findings", []):
        message = str(finding.get("message") or "").strip()
        if message:
            messages.append(message)
    return messages


def _report_attention_required(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    if report.get("attention_required"):
        return True
    if report.get("overall_blocked"):
        return True
    return bool(report.get("findings"))


def _clamp_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def _sha1_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()
