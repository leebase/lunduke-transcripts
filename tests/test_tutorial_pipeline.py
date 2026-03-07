from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from lunduke_transcripts.app.tutorial_agent_registry import TutorialAgentRegistry
from lunduke_transcripts.app.tutorial_pipeline import TutorialPipeline


class FakeTutorialLLM:
    def __init__(self, *, json_responses, text_responses, prompt_version="v1") -> None:
        self.json_responses = {
            key: [deepcopy(item) for item in value]
            for key, value in json_responses.items()
        }
        self.text_responses = {
            key: [str(item) for item in value] for key, value in text_responses.items()
        }
        self.provider = "openai"
        self.model = "gpt-4.1-mini"
        self.prompt_version = prompt_version
        self.calls: list[str] = []

    def is_enabled(self) -> bool:
        return True

    def run_json_task(self, *, task_name: str, system_prompt: str, user_prompt: str):
        _ = (system_prompt, user_prompt)
        self.calls.append(task_name)
        queue = self.json_responses[task_name]
        return deepcopy(queue.pop(0)), self.model, self.prompt_version

    def run_text_task(self, *, task_name: str, system_prompt: str, user_prompt: str):
        _ = (system_prompt, user_prompt)
        self.calls.append(task_name)
        queue = self.text_responses[task_name]
        return queue.pop(0), self.model, self.prompt_version


def test_tutorial_pipeline_requires_outline_approval(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
        },
        text_responses={},
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
        ),
    )

    summary = pipeline.run(bundle_path=bundle_path, approve_outline=False)

    assert summary.status == "awaiting_outline_approval"
    assert summary.publish_eligible is False
    tutorial_dir = bundle_path.parent / "tutorial"
    assert (tutorial_dir / "tutorial_definition.json").exists()
    assert (tutorial_dir / "lesson_outline.json").exists()
    assert (tutorial_dir / "evidence_map.json").exists()
    assert (tutorial_dir / "frame_selection_plan.json").exists()
    assert not (tutorial_dir / "tutorial_draft.md").exists()


def test_tutorial_pipeline_publishes_and_records_agent_versions(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={"tutorial.writer": [_draft_markdown()]},
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    summary = pipeline.run(bundle_path=bundle_path, approve_outline=True)

    assert summary.status == "published"
    assert summary.publish_eligible is True
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["human_outline_approved"] is True
    assert manifest["publish_eligible"] is True
    assert manifest["agents"]["educator"]["skills"]
    assert (summary.tutorial_dir / "tutorial_final.md").exists()


def test_adversarial_block_creates_revision_plan_and_blocks_publish(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence(), _evidence()],
            "tutorial.visual": [_visual(), _visual()],
            "tutorial.technical-review": [
                _technical_review(),
                _technical_review(),
            ],
            "tutorial.adversarial-review": [
                _adversarial_review(
                    overall_blocked=True,
                    findings=[
                        {
                            "severity": "blocking",
                            "category": "source_fidelity",
                            "message": (
                                "Draft claims a step not grounded in transcript."
                            ),
                            "step_id": "step-1",
                            "reroute_target": "evidence-mapper",
                        }
                    ],
                    recommended_reroute="evidence-mapper",
                ),
                _adversarial_review(
                    overall_blocked=True,
                    findings=[
                        {
                            "severity": "blocking",
                            "category": "source_fidelity",
                            "message": "Still unsupported after rewrite.",
                            "step_id": "step-1",
                            "reroute_target": "evidence-mapper",
                        }
                    ],
                    recommended_reroute="evidence-mapper",
                ),
            ],
        },
        text_responses={
            "tutorial.writer": [_draft_markdown(), _draft_markdown()],
        },
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=1,
    )

    assert summary.status == "blocked"
    assert summary.publish_eligible is False
    revision_plan = json.loads(
        (summary.tutorial_dir / "tutorial_revision_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert revision_plan["rerun_from_stage"] == "evidence-mapper"
    assert "Still unsupported after rewrite." in summary.failures[0]


def test_prose_only_issue_reroutes_to_writer_and_recovers(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [
                _technical_review(
                    overall_blocked=True,
                    findings=[
                        {
                            "severity": "high",
                            "category": "clarity",
                            "message": "Opening step is too terse.",
                            "step_id": "step-1",
                            "reroute_target": "script-writer",
                        }
                    ],
                ),
                _technical_review(),
            ],
            "tutorial.adversarial-review": [
                _adversarial_review(),
                _adversarial_review(),
            ],
        },
        text_responses={
            "tutorial.writer": [
                "# Demo Tutorial\n\n## Step 1\n\nToo short.\n",
                _draft_markdown(),
            ]
        },
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=1,
    )

    assert summary.status == "published"
    revision_plan = json.loads(
        (summary.tutorial_dir / "tutorial_revision_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert revision_plan["rerun_from_stage"] == "script-writer"


def test_tutorial_pipeline_reuses_cached_outputs_when_unchanged(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={"tutorial.writer": [_draft_markdown()]},
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    first = pipeline.run(bundle_path=bundle_path, approve_outline=True)
    calls_after_first = list(llm.calls)
    second = pipeline.run(bundle_path=bundle_path, approve_outline=True)

    assert first.status == "published"
    assert second.reused_cached_outputs is True
    assert llm.calls == calls_after_first


def test_text_only_steps_require_justification(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path, with_frames=False)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "selected_frame_path": None,
                            "caption": "",
                            "alt_text": "",
                            "support_strength": "text_only",
                            "text_only": True,
                            "text_only_reason": "",
                            "notes": "",
                        }
                    ]
                }
            ],
        },
        text_responses={"tutorial.writer": [_draft_markdown()]},
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    assert summary.status == "blocked"
    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["overall_blocked"] is True
    assert validation["findings"][0]["category"] == "missing_text_only_justification"


def test_skill_digest_changes_are_recorded_in_manifest(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm_one = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={"tutorial.writer": [_draft_markdown()]},
    )
    pipeline_one = TutorialPipeline(
        llm=llm_one,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )
    first = pipeline_one.run(bundle_path=bundle_path, approve_outline=True)
    manifest_one = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    original_digest = manifest_one["agents"]["educator"]["skills"][0]["digest"]

    skill_path = skills_dir / "definition-of-done.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8"
    )

    llm_two = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={"tutorial.writer": [_draft_markdown()]},
        prompt_version="v2",
    )
    pipeline_two = TutorialPipeline(
        llm=llm_two,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )
    second = pipeline_two.run(bundle_path=bundle_path, approve_outline=True)
    manifest_two = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    changed_digest = manifest_two["agents"]["educator"]["skills"][0]["digest"]

    assert changed_digest != original_digest
    assert second.reused_cached_outputs is False


def _make_bundle(tmp_path: Path, *, with_frames: bool = True) -> Path:
    video_dir = tmp_path / "video"
    video_dir.mkdir()
    transcript = {
        "schema_version": "1",
        "title": "Demo Video",
        "language": "en",
        "transcript_source": "manual",
        "segments": [
            {
                "segment_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "start_timestamp": "00:00:00.000",
                "end_timestamp": "00:00:02.000",
                "text": "Open the terminal.",
            },
            {
                "segment_index": 1,
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "start_timestamp": "00:00:02.000",
                "end_timestamp": "00:00:04.000",
                "text": "Run the command.",
            },
        ],
    }
    (video_dir / "transcript.json").write_text(
        json.dumps(transcript, indent=2) + "\n", encoding="utf-8"
    )
    if with_frames:
        frames_dir = video_dir / "frames"
        frames_dir.mkdir()
        (frames_dir / "000000.jpg").write_text("frame", encoding="utf-8")
        frame_manifest = {
            "schema_version": "1",
            "frames": [
                {
                    "frame_index": 0,
                    "timestamp_seconds": 1.0,
                    "timestamp": "00:00:01.000",
                    "image_path": "frames/000000.jpg",
                }
            ],
        }
        (video_dir / "frame_manifest.json").write_text(
            json.dumps(frame_manifest, indent=2) + "\n", encoding="utf-8"
        )
        frame_manifest_path = "frame_manifest.json"
    else:
        frame_manifest_path = None
    bundle = {
        "schema_version": "1",
        "source_id": "local-demo",
        "source_kind": "local_file",
        "title": "Demo Video",
        "metadata_path": "metadata.json",
        "transcript_path": "transcript.json",
        "frame_manifest_path": frame_manifest_path,
    }
    (video_dir / "metadata.json").write_text("{}", encoding="utf-8")
    bundle_path = video_dir / "tutorial_asset_bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return bundle_path


def _make_agent_files(tmp_path: Path) -> tuple[Path, Path]:
    agents_dir = tmp_path / "agents"
    skills_dir = tmp_path / "skills"
    agents_dir.mkdir()
    skills_dir.mkdir()
    agents = {
        "educator.md": (
            "# Agent: educator\n\nSkills:\n- definition-of-done\n- grounding\n"
        ),
        "tutorial-planner.md": (
            "# Agent: tutorial-planner\n\n"
            "Skills:\n- tutorial-planning\n- grounding\n"
        ),
        "evidence-mapper.md": (
            "# Agent: evidence-mapper\n\n" "Skills:\n- evidence-mapping\n- grounding\n"
        ),
        "script-writer.md": (
            "# Agent: script-writer\n\nSkills:\n- tutorial-writing\n- grounding\n"
        ),
        "visual-editor.md": (
            "# Agent: visual-editor\n\nSkills:\n- frame-selection\n- grounding\n"
        ),
        "validator.md": "# Agent: validator\n\nSkills:\n- tutorial-validation\n",
        "technical-reviewer.md": (
            "# Agent: technical-reviewer\n\n"
            "Skills:\n- technical-review\n- grounding\n"
        ),
        "adversarial-reviewer.md": (
            "# Agent: adversarial-reviewer\n\nSkills:\n"
            "- source-grounding-attack\n- learner-confusion-attack\n"
        ),
        "review-responder.md": (
            "# Agent: review-responder\n\nSkills:\n- review-response\n"
        ),
    }
    skills = {
        "definition-of-done.md": "definition",
        "grounding.md": "grounding",
        "tutorial-planning.md": "planning",
        "evidence-mapping.md": "evidence",
        "tutorial-writing.md": "writing",
        "frame-selection.md": "frames",
        "tutorial-validation.md": "validation",
        "technical-review.md": "tech",
        "source-grounding-attack.md": "ground attack",
        "learner-confusion-attack.md": "learner attack",
        "review-response.md": "review response",
    }
    for filename, content in agents.items():
        (agents_dir / filename).write_text(content, encoding="utf-8")
    for filename, content in skills.items():
        (skills_dir / filename).write_text(content, encoding="utf-8")
    return agents_dir, skills_dir


def _definition() -> dict[str, object]:
    return {
        "target_audience": "technical_user",
        "learning_objectives": ["Open the terminal and run the command."],
        "prerequisites": ["Basic shell access."],
        "success_criteria": ["The command runs successfully."],
        "allowed_enrichment_level": "light",
        "evidence_requirements": {
            "transcript_support_required": True,
            "unsupported_factual_claims_block": True,
        },
        "visual_requirements": {
            "weak_visual_support_blocks": True,
            "text_only_requires_justification": True,
        },
        "blocking_conditions": ["unsupported facts"],
        "output_targets": ["markdown"],
    }


def _outline() -> dict[str, object]:
    return {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Get Started",
                "goal": "Run the command",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Open the terminal",
                        "instruction": (
                            "Open the terminal and prepare to run the command."
                        ),
                        "assumptions": ["A shell is available."],
                        "text_only_allowed": False,
                    }
                ],
            }
        ]
    }


def _evidence() -> dict[str, object]:
    return {
        "steps": [
            {
                "step_id": "step-1",
                "segment_indexes": [0, 1],
                "evidence_strength": "strong",
                "supporting_quote": "Open the terminal. Run the command.",
                "assumptions": ["A shell is available."],
                "notes": "",
            }
        ]
    }


def _visual() -> dict[str, object]:
    return {
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Terminal open before the command is run.",
                "alt_text": "Terminal window prepared for the command.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            }
        ]
    }


def _draft_markdown() -> str:
    return (
        "# Demo Tutorial\n\n"
        "## Open the terminal\n\n"
        "Open the terminal and run the command shown in the video.\n\n"
        "![Terminal window prepared for the command.](../frames/000000.jpg)\n"
    )


def _technical_review(
    *, overall_blocked: bool = False, findings: list[dict[str, object]] | None = None
) -> dict[str, object]:
    return {
        "overall_blocked": overall_blocked,
        "findings": findings or [],
    }


def _adversarial_review(
    *,
    overall_blocked: bool = False,
    findings: list[dict[str, object]] | None = None,
    recommended_reroute: str = "script-writer",
) -> dict[str, object]:
    return {
        "source_fidelity_score": 1.0 if not overall_blocked else 0.2,
        "teachability_score": 1.0 if not overall_blocked else 0.4,
        "visual_support_score": 1.0 if not overall_blocked else 0.4,
        "overall_blocked": overall_blocked,
        "recommended_reroute": recommended_reroute,
        "findings": findings or [],
    }
