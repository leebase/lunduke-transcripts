from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from lunduke_transcripts.app.tutorial_agent_registry import TutorialAgentRegistry
from lunduke_transcripts.app.tutorial_pipeline import (
    TutorialPipeline,
    _apply_frame_selection_plan_to_draft,
    _apply_public_editorial_pass,
    _normalize_definition,
    _normalize_frame_selection_plan,
    _normalize_outline_assumptions,
    _refit_frame_selection_plan_to_draft,
    _step_matches_reference,
)


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
        if task_name not in self.json_responses:
            if task_name == "tutorial.source-interpretation":
                return (
                    deepcopy(_source_interpretation()),
                    self.model,
                    self.prompt_version,
                )
            raise KeyError(task_name)
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
    assert (tutorial_dir / "source_interpretation.json").exists()
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
    assert manifest["agents"]["source-interpreter"]["skills"]
    assert (summary.tutorial_dir / "source_interpretation.json").exists()
    assert (summary.tutorial_dir / "tutorial_final.md").exists()


def test_source_interpretation_stage_runs_and_is_recorded(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Run the transcript pipeline on a channel.",
                    "learner_payoff": (
                        "Get transcript artifacts without manual scraping."
                    ),
                    "best_first_action": "Run the pipeline command with a config file.",
                    "steps_to_emphasize": [
                        "Run the command",
                        "Inspect the generated transcript artifacts",
                    ],
                    "steps_to_demote": [
                        "Desktop setup",
                        "project folder naming",
                    ],
                    "incidental_context": ["The video was recorded on a Mac mini."],
                    "terminology_notes": ["Use Codex, not codecs."],
                }
            ],
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

    assert "tutorial.source-interpretation" in llm.calls
    interpretation = json.loads(
        (summary.tutorial_dir / "source_interpretation.json").read_text(
            encoding="utf-8"
        )
    )
    assert interpretation["best_first_action"] == (
        "Run the pipeline command with a config file."
    )
    assert "codecs" not in json.dumps(interpretation).lower()
    assert "Codex" in json.dumps(interpretation)


def test_source_interpretation_demotes_setup_first_action(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Build and run the transcript pipeline.",
                    "learner_payoff": "Understand the workflow and produce output.",
                    "best_first_action": "Create a new project folder.",
                    "steps_to_emphasize": [
                        "Create a new project folder.",
                        "Run the pipeline command against a configured target.",
                    ],
                    "steps_to_demote": ["Remote desktop details."],
                    "incidental_context": ["The recording used a Mac mini."],
                    "terminology_notes": [],
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    interpretation = json.loads(
        (summary.tutorial_dir / "source_interpretation.json").read_text(
            encoding="utf-8"
        )
    )
    assert interpretation["best_first_action"] == (
        "Run the pipeline command against a configured target."
    )
    assert "Create a new project folder." in interpretation["steps_to_demote"]


def test_adversarial_findings_trigger_reroute_and_recover(tmp_path) -> None:
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
                    attention_required=True,
                    findings=[
                        {
                            "severity": "high",
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
                _adversarial_review(),
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

    assert summary.status == "published"
    assert summary.publish_eligible is True
    assert summary.review_cycles == 1
    assert llm.calls.count("tutorial.evidence") == 2


def test_adversarial_findings_do_not_block_after_retry_budget(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [
                _adversarial_review(
                    attention_required=True,
                    findings=[
                        {
                            "severity": "high",
                            "category": "source_fidelity",
                            "message": "Caution: one step remains thinly supported.",
                            "step_id": "step-1",
                            "reroute_target": "script-writer",
                        }
                    ],
                )
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

    assert summary.status == "published"
    assert summary.publish_eligible is True
    assert summary.failures == ["Caution: one step remains thinly supported."]
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["review_outcomes"]["adversarial_blocked"] is False
    assert manifest["review_outcomes"]["adversarial_attention_required"] is True


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
                '<a id="top"></a>\n\n'
                "# Demo Tutorial\n\n"
                "## What This Tutorial Is For\n\n"
                "Short intro.\n\n"
                "## Table of Contents\n\n"
                "- [Step 1](#step-1)\n\n"
                '<a id="step-1"></a>\n\n'
                "## Step 1\n\n"
                "Too short.\n\n"
                "[Back to top](#top)\n",
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
    assert llm.calls.count("tutorial.writer") == 2
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    assert summary.status == "published"
    assert summary.publish_eligible is True
    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["overall_blocked"] is True
    assert validation["findings"][0]["category"] == "missing_text_only_justification"
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["review_outcomes"]["validation_attention_required"] is True


def test_final_tutorial_rejects_evidence_leakage_and_missing_navigation(
    tmp_path,
) -> None:
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
        text_responses={
            "tutorial.writer": [
                "# Demo Tutorial\n\n"
                "## Step 1\n\n"
                "> **Evidence:** transcript says to do it.\n\n"
                "The speaker says to run the command.\n\n"
                "![Terminal](../frames/000000.jpg)\n"
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
        max_review_cycles=0,
    )

    assert summary.status == "published"
    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {finding["category"] for finding in validation["findings"]}
    assert "missing_context_section" in categories
    assert "missing_table_of_contents" in categories
    assert "evidence_leakage" in categories


def test_final_tutorial_flags_known_term_confusions(tmp_path) -> None:
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
        text_responses={
            "tutorial.writer": [
                '<a id="top"></a>\n\n'
                "# Demo Tutorial\n\n"
                "## What This Tutorial Is For\n\n"
                "This tutorial shows how to use GPT 5.3 codecs in the workflow.\n\n"
                "[Back to top](#top)\n\n"
                "## Table of Contents\n\n"
                "- [Open the terminal](#open-the-terminal)\n\n"
                '<a id="open-the-terminal"></a>\n\n'
                "## Open the terminal\n\n"
                "This section covers codecs in the project workflow.\n\n"
                "![Terminal window prepared for the command.](../frames/000000.jpg)\n\n"
                "*Introduction to the tutorial covering codecs and setup.*\n\n"
                "[Back to top](#top)\n"
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
        max_review_cycles=0,
    )

    assert summary.status == "published"
    final_markdown = (summary.tutorial_dir / "tutorial_final.md").read_text(
        encoding="utf-8"
    )
    assert "codecs" not in final_markdown.lower()
    assert "Codex" in final_markdown
    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    terminology_categories = [finding["category"] for finding in validation["findings"]]
    assert "terminology" not in terminology_categories


def test_definition_flags_control_public_tutorial_validation(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [
                _definition(
                    context_section_required=False,
                    table_of_contents_required=False,
                    back_to_top_links_required=False,
                )
            ],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={
            "tutorial.writer": [
                "# Demo Tutorial\n\n"
                "## Open the terminal\n\n"
                "Open the terminal and run the command shown in the video.\n\n"
                "![Terminal window prepared for the command.](../frames/000000.jpg)\n"
            ]
        },
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    summary = pipeline.run(bundle_path=bundle_path, approve_outline=True)

    assert summary.status == "published"
    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {finding["category"] for finding in validation["findings"]}
    assert "missing_context_section" not in categories
    assert "missing_table_of_contents" not in categories
    assert "missing_back_to_top_links" not in categories


def test_each_major_section_requires_back_to_top_link(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline_with_two_steps()],
            "tutorial.evidence": [_evidence_with_two_steps()],
            "tutorial.visual": [_visual_with_two_steps()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={
            "tutorial.writer": [
                (
                    '<a id="top"></a>\n\n'
                    "# Demo Tutorial\n\n"
                    "## What This Tutorial Is For\n\n"
                    "This tutorial shows you what the workflow does and what "
                    "you get from it.\n\n"
                    "## Table of Contents\n\n"
                    "- [Open the terminal](#open-the-terminal)\n"
                    "- [Run the command](#run-the-command)\n\n"
                    '<a id="open-the-terminal"></a>\n\n'
                    "## Open the terminal\n\n"
                    "Open the terminal and get ready.\n\n"
                    "![Terminal window prepared for the command.]"
                    "(../frames/000000.jpg)\n\n"
                    "[Back to top](#top)\n\n"
                    '<a id="run-the-command"></a>\n\n'
                    "## Run the command\n\n"
                    "Run the command from the video.\n\n"
                    "![Command running in the terminal.](../frames/000001.jpg)\n"
                )
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
        max_review_cycles=0,
    )

    assert summary.status == "published"
    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    messages = [finding["message"] for finding in validation["findings"]]
    assert any("Run the command" in message for message in messages)


def test_validator_flags_incidental_setup_before_core_workflow(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Get Connected",
                            "goal": "Join the machine",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "SSH into the remote machine",
                                    "instruction": (
                                        "Open an SSH session to the remote desktop "
                                        "machine used for recording."
                                    ),
                                    "assumptions": ["SSH access is available."],
                                    "text_only_allowed": False,
                                },
                                {
                                    "step_id": "step-2",
                                    "title": "Run the command",
                                    "instruction": "Run the command from the workflow.",
                                    "assumptions": ["A shell is available."],
                                    "text_only_allowed": False,
                                },
                            ],
                        }
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "SSH into the machine.",
                            "assumptions": ["SSH access is available."],
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "segment_indexes": [1],
                            "evidence_strength": "strong",
                            "supporting_quote": "Run the command.",
                            "assumptions": ["A shell is available."],
                            "notes": "",
                        },
                    ]
                }
            ],
            "tutorial.visual": [_visual_with_two_steps()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={
            "tutorial.writer": [
                (
                    '<a id="top"></a>\n\n'
                    "# Demo Tutorial\n\n"
                    "## What This Tutorial Is For\n\n"
                    "This tutorial shows the real workflow and why it matters.\n\n"
                    "## Table of Contents\n\n"
                    "- [SSH into the remote machine](#ssh-into-the-remote-machine)\n"
                    "- [Run the command](#run-the-command)\n\n"
                    '<a id="ssh-into-the-remote-machine"></a>\n\n'
                    "## SSH into the remote machine\n\n"
                    "Open an SSH session to the machine used for recording.\n\n"
                    "![Terminal window prepared for the command.]"
                    "(../frames/000000.jpg)\n\n"
                    "[Back to top](#top)\n\n"
                    '<a id="run-the-command"></a>\n\n'
                    "## Run the command\n\n"
                    "Run the command from the workflow.\n\n"
                    "![Command running in the terminal.](../frames/000001.jpg)\n\n"
                    "[Back to top](#top)\n"
                )
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
        max_review_cycles=0,
    )

    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {finding["category"] for finding in validation["findings"]}
    assert "incidental_setup_priority" in categories


def test_validator_flags_outline_when_it_ignores_interpreted_first_action(
    tmp_path,
) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Run the transcript pipeline.",
                    "learner_payoff": "Generate transcript artifacts.",
                    "best_first_action": "Inspect the generated artifacts.",
                    "steps_to_emphasize": [
                        "Inspect the generated artifacts.",
                        "Verify the generated transcript output.",
                    ],
                    "steps_to_demote": [
                        "Create a new project folder.",
                    ],
                    "incidental_context": ["The video was recorded remotely."],
                    "terminology_notes": [],
                }
            ],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Get Started",
                            "goal": "Start the project",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "Create a new project folder",
                                    "instruction": (
                                        "Create a new project folder before "
                                        "doing anything else."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                },
                                {
                                    "step_id": "step-2",
                                    "title": "Run the pipeline command",
                                    "instruction": "Run the pipeline command.",
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                },
                            ],
                        }
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "Create the folder.",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "segment_indexes": [1],
                            "evidence_strength": "strong",
                            "supporting_quote": "Run the pipeline command.",
                            "assumptions": [],
                            "notes": "",
                        },
                    ]
                }
            ],
            "tutorial.visual": [_visual_with_two_steps()],
            "tutorial.technical-review": [_technical_review()],
            "tutorial.adversarial-review": [_adversarial_review()],
        },
        text_responses={
            "tutorial.writer": [
                (
                    '<a id="top"></a>\n\n'
                    "# Demo Tutorial\n\n"
                    "## What This Tutorial Is For\n\n"
                    "This tutorial shows how to run the workflow.\n\n"
                    "## Table of Contents\n\n"
                    "- [Create a new project folder](#create-a-new-project-folder)\n"
                    "- [Run the pipeline command](#run-the-pipeline-command)\n\n"
                    '<a id="create-a-new-project-folder"></a>\n\n'
                    "## Create a new project folder\n\n"
                    "Create a new project folder before doing anything else.\n\n"
                    "![Terminal window prepared for the command.]"
                    "(../frames/000000.jpg)\n\n"
                    "[Back to top](#top)\n\n"
                    '<a id="run-the-pipeline-command"></a>\n\n'
                    "## Run the pipeline command\n\n"
                    "Run the pipeline command.\n\n"
                    "![Command running in the terminal.](../frames/000001.jpg)\n\n"
                    "[Back to top](#top)\n"
                )
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
        max_review_cycles=0,
    )

    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {finding["category"] for finding in validation["findings"]}
    assert "outline_misaligned_with_interpretation" in categories
    assert "outline_promotes_demoted_setup" in categories


def test_outline_normalization_reorders_same_section_to_best_first_action(
    tmp_path,
) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Use AI to plan the transcript project.",
                    "learner_payoff": "Start the project with the right workflow.",
                    "best_first_action": (
                        "Engage the AI as a co-thinker to define project goals."
                    ),
                    "steps_to_emphasize": [
                        "Engage the AI as a co-thinker to define project goals.",
                        "Review the product definition.",
                    ],
                    "steps_to_demote": [
                        "Create a new project folder.",
                    ],
                    "incidental_context": ["The demo was recorded remotely."],
                    "terminology_notes": [],
                }
            ],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Introduction",
                            "goal": "Orient the reader",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "What This Tutorial Is For",
                                    "instruction": "This tutorial shows the workflow.",
                                    "assumptions": [],
                                    "text_only_allowed": True,
                                }
                            ],
                        },
                        {
                            "section_id": "section-2",
                            "title": "Getting Started",
                            "goal": "Start the project",
                            "steps": [
                                {
                                    "step_id": "step-2",
                                    "title": "Create a new project folder",
                                    "instruction": "Create a new project folder.",
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                },
                                {
                                    "step_id": "step-3",
                                    "title": (
                                        "Engage AI as a co-thinker to define "
                                        "project goals"
                                    ),
                                    "instruction": (
                                        "Start a conversation with the AI to "
                                        "define the project goals."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                },
                            ],
                        },
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "Orientation.",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "segment_indexes": [1],
                            "evidence_strength": "strong",
                            "supporting_quote": "Create a folder.",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-3",
                            "segment_indexes": [2],
                            "evidence_strength": "strong",
                            "supporting_quote": "Engage the AI.",
                            "assumptions": [],
                            "notes": "",
                        },
                    ]
                }
            ],
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
                            "text_only_reason": "Intro is text only.",
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "selected_frame_path": "frames/000000.jpg",
                            "caption": "Project folder setup.",
                            "alt_text": "Project folder setup.",
                            "support_strength": "strong",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        },
                        {
                            "step_id": "step-3",
                            "selected_frame_path": "frames/000001.jpg",
                            "caption": "AI planning conversation.",
                            "alt_text": "AI planning conversation.",
                            "support_strength": "strong",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        },
                    ]
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    outline = json.loads(
        (summary.tutorial_dir / "lesson_outline.json").read_text(encoding="utf-8")
    )
    actionable_titles = [
        step["title"]
        for section in outline["sections"]
        for step in section["steps"]
        if not step["text_only_allowed"]
    ]
    assert actionable_titles[0] == "Engage AI as a co-thinker to define project goals"


def test_outline_normalization_moves_best_first_action_ahead_of_text_only_setup(
    tmp_path,
) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Use AI to plan the transcript project.",
                    "learner_payoff": "Start with the real workflow.",
                    "best_first_action": (
                        "Engage the AI as a co-thinker to define project goals."
                    ),
                    "steps_to_emphasize": [
                        "Engage the AI as a co-thinker to define project goals."
                    ],
                    "steps_to_demote": ["Create a new project folder."],
                    "incidental_context": [],
                    "terminology_notes": [],
                }
            ],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Introduction",
                            "goal": "Orient the reader",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "What This Tutorial Is For",
                                    "instruction": "This tutorial shows the workflow.",
                                    "assumptions": [],
                                    "text_only_allowed": True,
                                }
                            ],
                        },
                        {
                            "section_id": "section-2",
                            "title": "Getting Started",
                            "goal": "Start the project",
                            "steps": [
                                {
                                    "step_id": "step-2",
                                    "title": "Create a new project folder",
                                    "instruction": "Create a new project folder.",
                                    "assumptions": [],
                                    "text_only_allowed": True,
                                },
                                {
                                    "step_id": "step-3",
                                    "title": (
                                        "Engage AI as a co-thinker to define "
                                        "project goals"
                                    ),
                                    "instruction": (
                                        "Start a conversation with the AI to "
                                        "define the project goals."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                },
                            ],
                        },
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "Orientation.",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "segment_indexes": [1],
                            "evidence_strength": "strong",
                            "supporting_quote": "Create a folder.",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-3",
                            "segment_indexes": [2],
                            "evidence_strength": "strong",
                            "supporting_quote": "Engage the AI.",
                            "assumptions": [],
                            "notes": "",
                        },
                    ]
                }
            ],
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
                            "text_only_reason": "Intro is text only.",
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "selected_frame_path": None,
                            "caption": "",
                            "alt_text": "",
                            "support_strength": "text_only",
                            "text_only": True,
                            "text_only_reason": "Folder setup is context only.",
                            "notes": "",
                        },
                        {
                            "step_id": "step-3",
                            "selected_frame_path": "frames/000001.jpg",
                            "caption": "AI planning conversation.",
                            "alt_text": "AI planning conversation.",
                            "support_strength": "strong",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        },
                    ]
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    outline = json.loads(
        (summary.tutorial_dir / "lesson_outline.json").read_text(encoding="utf-8")
    )
    step_titles = [step["title"] for step in outline["sections"][1]["steps"]]
    assert step_titles == [
        "Engage AI as a co-thinker to define project goals",
        "Create a new project folder",
    ]


def test_outline_validation_ignores_intro_context_for_best_first_alignment(
    tmp_path,
) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Use AI to plan the transcript project.",
                    "learner_payoff": "Start with the real workflow.",
                    "best_first_action": (
                        "Engage the AI as a co-thinker to define project goals."
                    ),
                    "steps_to_emphasize": [
                        "Engage the AI as a co-thinker to define project goals."
                    ],
                    "steps_to_demote": [],
                    "incidental_context": [],
                    "terminology_notes": [],
                }
            ],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Introduction",
                            "goal": "Orient the reader",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "What This Tutorial Is For",
                                    "instruction": "This tutorial shows the workflow.",
                                    "assumptions": [],
                                    "text_only_allowed": True,
                                }
                            ],
                        },
                        {
                            "section_id": "section-2",
                            "title": "Getting Started",
                            "goal": "Start the project",
                            "steps": [
                                {
                                    "step_id": "step-2",
                                    "title": (
                                        "Engage AI as a co-thinker to define "
                                        "project goals"
                                    ),
                                    "instruction": (
                                        "Start a conversation with the AI to "
                                        "define the project goals."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                }
                            ],
                        },
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "Orientation.",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "segment_indexes": [1],
                            "evidence_strength": "strong",
                            "supporting_quote": "Engage the AI.",
                            "assumptions": [],
                            "notes": "",
                        },
                    ]
                }
            ],
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
                            "text_only_reason": "Intro is text only.",
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "selected_frame_path": "frames/000001.jpg",
                            "caption": "AI planning conversation.",
                            "alt_text": "AI planning conversation.",
                            "support_strength": "strong",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        },
                    ]
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {finding["category"] for finding in validation["findings"]}
    assert "outline_misaligned_with_interpretation" not in categories


def test_outline_validation_ignores_non_text_intro_context_for_best_first_alignment(
    tmp_path,
) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.source-interpretation": [
                {
                    "core_workflow": "Use AI to plan the transcript project.",
                    "learner_payoff": "Start with the real workflow.",
                    "best_first_action": (
                        "Engage the AI as a co-thinker to define project goals."
                    ),
                    "steps_to_emphasize": [
                        "Engage the AI as a co-thinker to define project goals."
                    ],
                    "steps_to_demote": [],
                    "incidental_context": [],
                    "terminology_notes": [],
                }
            ],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Introduction",
                            "goal": "Orient the reader",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "What You Will Have by the End",
                                    "instruction": (
                                        "Explain what the reader will understand "
                                        "by the end."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                }
                            ],
                        },
                        {
                            "section_id": "section-2",
                            "title": "Getting Started",
                            "goal": "Start the project",
                            "steps": [
                                {
                                    "step_id": "step-2",
                                    "title": (
                                        "Engage AI as a co-thinker to define "
                                        "project goals"
                                    ),
                                    "instruction": (
                                        "Start a conversation with the AI to "
                                        "define the project goals."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                }
                            ],
                        },
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "By the end...",
                            "assumptions": [],
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "segment_indexes": [1],
                            "evidence_strength": "strong",
                            "supporting_quote": "Engage the AI.",
                            "assumptions": [],
                            "notes": "",
                        },
                    ]
                }
            ],
            "tutorial.visual": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "selected_frame_path": "frames/000000.jpg",
                            "caption": "Intro context.",
                            "alt_text": "Intro context.",
                            "support_strength": "strong",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        },
                        {
                            "step_id": "step-2",
                            "selected_frame_path": "frames/000001.jpg",
                            "caption": "AI planning conversation.",
                            "alt_text": "AI planning conversation.",
                            "support_strength": "strong",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        },
                    ]
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {finding["category"] for finding in validation["findings"]}
    assert "outline_misaligned_with_interpretation" not in categories


def test_outline_copyedits_known_term_confusions(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Start with AI codecs",
                            "goal": "Use codecs in the workflow",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "Open GPT codecs",
                                    "instruction": (
                                        "Use AI codecs to plan the workflow."
                                    ),
                                    "assumptions": [
                                        "GPT codecs is available in your account."
                                    ],
                                    "text_only_allowed": True,
                                }
                            ],
                        }
                    ]
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    outline = json.loads(
        (summary.tutorial_dir / "lesson_outline.json").read_text(encoding="utf-8")
    )
    outline_text = json.dumps(outline)
    assert "codecs" not in outline_text.lower()
    assert "Codex" in outline_text


def test_step_title_representation_uses_slug_and_keyword_signal(tmp_path) -> None:
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
        text_responses={
            "tutorial.writer": [
                (
                    '<a id="top"></a>\n\n'
                    "# Demo Tutorial\n\n"
                    "## What This Tutorial Is For\n\n"
                    "This tutorial shows you what the workflow does and what "
                    "you get from it.\n\n"
                    "## Table of Contents\n\n"
                    "- [Open the terminal](#open-the-terminal)\n\n"
                    '<a id="open-the-terminal"></a>\n\n'
                    "## Get Ready\n\n"
                    "Open the terminal and run the command shown in the video.\n\n"
                    "![Terminal window prepared for the command.]"
                    "(../frames/000000.jpg)\n\n"
                    "*Terminal ready for the command.*\n\n"
                    "[Back to top](#top)\n"
                )
            ]
        },
    )
    pipeline = TutorialPipeline(
        llm=llm,
        agent_registry=TutorialAgentRegistry(
            agents_dir=agents_dir, skills_dir=skills_dir
        ),
    )

    summary = pipeline.run(bundle_path=bundle_path, approve_outline=True)

    validation = json.loads(
        (summary.tutorial_dir / "tutorial_validation_report.json").read_text(
            encoding="utf-8"
        )
    )
    messages = [finding["message"] for finding in validation["findings"]]
    assert "Step title is not clearly represented in the draft." not in messages


def test_validation_findings_do_not_skip_other_reviews(tmp_path) -> None:
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
                    findings=[
                        {
                            "severity": "medium",
                            "category": "completeness",
                            "message": "Explain the command outcome more clearly.",
                            "step_id": "step-1",
                            "reroute_target": "script-writer",
                        }
                    ]
                )
            ],
            "tutorial.adversarial-review": [
                _adversarial_review(
                    attention_required=True,
                    findings=[
                        {
                            "severity": "high",
                            "category": "source_fidelity",
                            "message": "One claim needs better grounding.",
                            "step_id": "step-1",
                            "reroute_target": "script-writer",
                        }
                    ],
                )
            ],
        },
        text_responses={
            "tutorial.writer": [
                "# Demo Tutorial\n\n"
                "## Step 1\n\n"
                "> **Evidence:** transcript says to do it.\n\n"
                "The speaker says to run the command.\n\n"
                "![Terminal](../frames/000000.jpg)\n"
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
        max_review_cycles=0,
    )

    assert summary.status == "published"
    technical = json.loads(
        (summary.tutorial_dir / "technical_review_report.json").read_text(
            encoding="utf-8"
        )
    )
    adversarial = json.loads(
        (summary.tutorial_dir / "adversarial_review_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert technical.get("skipped") is not True
    assert adversarial.get("skipped") is not True
    assert technical["findings"]
    assert adversarial["findings"]


def test_public_editorial_pass_injects_workflow_patterns_and_strips_scaffolding() -> (
    None
):
    draft = (
        '<a id="top"></a>\n\n'
        "# Demo Tutorial\n\n"
        "## What This Tutorial Is For\n\n"
        "Context.\n\n"
        "This is a workflow tutorial, not a fully copy-paste setup guide. "
        "The source demonstrates the process clearly, but it does not provide "
        "every exact command, runtime flag, or environment configuration needed "
        "to reproduce the project verbatim in another setup.\n\n"
        "## Table of Contents\n\n"
        "- [Introduction and Tutorial Overview](#introduction-and-tutorial-overview)\n"
        "  - [What This Tutorial Is For](#what-this-tutorial-is-for-1)\n"
        "- [Define Product Goals with AI](#define-product-goals-with-ai)\n"
        "- [Text-Only and Visual Notes](#text-only-and-visual-notes)\n\n"
        "## Introduction and Tutorial Overview\n\n"
        "### What This Tutorial Is For\n\n"
        "This section repeats the intro heading.\n\n"
        "[Back to top](#top)\n\n"
        "### Define Product Goals with AI\n\n"
        "Set the goals for the utility.\n\n"
        "[Back to top](#top)\n\n"
        "### Text-Only and Visual Notes\n\n"
        "This should be removed.\n\n"
        "[Back to top](#top)\n"
    )
    outline = {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Planning",
                "goal": "Define the goals",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Define Product Goals with AI",
                        "instruction": "Set the goals for the utility.",
                        "text_only_allowed": False,
                    }
                ],
            }
        ]
    }
    frame_selection_plan = {
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": None,
                "text_only": True,
            }
        ]
    }

    revised = _apply_public_editorial_pass(
        draft,
        outline=outline,
        frame_selection_plan=frame_selection_plan,
    )

    assert "guided workflow walkthrough" in revised
    assert (
        "AI coding tool environment and a Python-capable project workspace" in revised
    )
    assert "### The Demonstrated Project" in revised
    assert "- [The Demonstrated Project](#the-demonstrated-project)" in revised
    assert "### What This Tutorial Is For" not in revised
    assert "Try this planning prompt:" not in revised
    assert "Artifact to keep:" not in revised
    assert "Text-Only and Visual Notes" not in revised


def test_definition_normalization_softens_prereqs_and_contract() -> None:
    definition = _normalize_definition(
        {
            "target_audience": "technical_user",
            "learning_objectives": [
                "Understand the process of using codecs as demonstrated in the video",
                "Follow step-by-step instructions to download transcripts",
            ],
            "prerequisites": [
                "Access to a Mac Mini or similar environment as shown in the video",
                (
                    "Understanding of what codecs and transcripts are in the "
                    "context of video processing"
                ),
                "Basic knowledge of AI interaction concepts",
            ],
            "success_criteria": [
                (
                    "The learner can initiate a new project folder and name it "
                    "appropriately"
                ),
                (
                    "The learner can follow step-by-step instructions to "
                    "download and manage YouTube video transcripts as demonstrated"
                ),
            ],
        }
    )

    assert "codecs" not in json.dumps(definition).lower()
    assert definition["learning_objectives"][1] == (
        "Follow demonstrated workflow instructions to download transcripts"
    )
    assert definition["prerequisites"] == [
        "Access to a terminal-based development environment.",
        (
            "Basic familiarity with what video transcripts are and with using "
            "an AI coding assistant."
        ),
        "Basic familiarity with using an AI coding assistant.",
    ]
    assert definition["success_criteria"][0] == (
        "The learner understands how the demonstrated workflow moves from a "
        "prepared workspace into AI-assisted planning."
    )
    assert "step-by-step" not in json.dumps(definition).lower()


def test_outline_assumptions_are_softened_to_minimal_supported_context() -> None:
    assumptions = _normalize_outline_assumptions(
        [
            "Project folder is pre-created or ready for use.",
            "You have access to Codex through ChatGPT Plus or equivalent.",
            "Familiarity with basic software architecture concepts.",
            "Understanding of sprint planning concepts.",
            "Access to environment variables or keys for AI services.",
        ]
    )

    assert assumptions == [
        "A project workspace is ready for use.",
        "You have access to Codex or a comparable AI coding assistant.",
        "Basic familiarity with technical project planning.",
        "Willingness to break work into small, trackable tasks.",
        "Access to any AI configuration the later formatting step requires.",
    ]


def test_weak_conceptual_visual_is_downgraded_to_text_only(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [
                {
                    "sections": [
                        {
                            "section_id": "section-1",
                            "title": "Planning",
                            "goal": "Plan the project",
                            "steps": [
                                {
                                    "step_id": "step-1",
                                    "title": "Create a Sprint Plan",
                                    "instruction": (
                                        "Break the work into testable steps."
                                    ),
                                    "assumptions": [],
                                    "text_only_allowed": False,
                                }
                            ],
                        }
                    ]
                }
            ],
            "tutorial.evidence": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "segment_indexes": [0],
                            "evidence_strength": "strong",
                            "supporting_quote": "Create a sprint plan.",
                            "assumptions": [],
                            "notes": "",
                        }
                    ]
                }
            ],
            "tutorial.visual": [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "selected_frame_path": "frames/000000.jpg",
                            "caption": "Generic terminal view.",
                            "alt_text": "Generic terminal view.",
                            "support_strength": "weak",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        }
                    ]
                }
            ],
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

    summary = pipeline.run(
        bundle_path=bundle_path,
        approve_outline=True,
        max_review_cycles=0,
    )

    frame_selection_plan = json.loads(
        (summary.tutorial_dir / "frame_selection_plan.json").read_text(encoding="utf-8")
    )
    step = frame_selection_plan["steps"][0]
    assert step["selected_frame_path"] is None
    assert step["text_only"] is True
    assert step["support_strength"] == "text_only"


def test_reused_frame_is_downgraded_for_later_steps() -> None:
    outline = {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Workflow",
                "goal": "Walk the project lifecycle",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Create a Sprint Plan",
                        "instruction": "Break the work into testable steps.",
                        "text_only_allowed": False,
                    },
                    {
                        "step_id": "step-2",
                        "title": "Review the Code",
                        "instruction": "Review the generated code in detail.",
                        "text_only_allowed": False,
                    },
                    {
                        "step_id": "step-3",
                        "title": "Iterate on Fixes",
                        "instruction": "Address the review findings.",
                        "text_only_allowed": False,
                    },
                    {
                        "step_id": "step-4",
                        "title": "Run the Application",
                        "instruction": "Execute the utility and inspect the output.",
                        "text_only_allowed": False,
                    },
                ],
            }
        ]
    }
    frame_manifest = {
        "frames": [
            {"image_path": "frames/000000.jpg"},
            {"image_path": "frames/000001.jpg"},
        ]
    }
    payload = {
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Shared terminal frame.",
                "alt_text": "Shared terminal frame.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
            {
                "step_id": "step-2",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Shared terminal frame.",
                "alt_text": "Shared terminal frame.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
            {
                "step_id": "step-3",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Shared terminal frame.",
                "alt_text": "Shared terminal frame.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
            {
                "step_id": "step-4",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Shared terminal frame.",
                "alt_text": "Shared terminal frame.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
        ]
    }

    plan = _normalize_frame_selection_plan(payload, outline, frame_manifest)

    assert plan["steps"][0]["selected_frame_path"] == "frames/000000.jpg"
    assert plan["steps"][1]["selected_frame_path"] is None
    assert plan["steps"][1]["text_only"] is True
    assert plan["steps"][1]["support_strength"] == "text_only"
    assert plan["steps"][2]["selected_frame_path"] is None
    assert plan["steps"][2]["text_only"] is True
    assert plan["steps"][3]["selected_frame_path"] == "frames/000000.jpg"
    assert plan["steps"][3]["support_strength"] == "weak"


def test_reused_frame_is_downgraded_even_when_only_two_steps_share_it() -> None:
    outline = {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Workflow",
                "goal": "Walk the project lifecycle",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Create a Design Note",
                        "instruction": "Clarify the architecture choices.",
                        "text_only_allowed": False,
                    },
                    {
                        "step_id": "step-2",
                        "title": "Download and Prepare YouTube Video Transcripts",
                        "instruction": "Work from transcript text in the project.",
                        "text_only_allowed": False,
                    },
                ],
            }
        ]
    }
    frame_manifest = {"frames": [{"image_path": "frames/000000.jpg"}]}
    payload = {
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Shared frame.",
                "alt_text": "Shared frame.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
            {
                "step_id": "step-2",
                "selected_frame_path": "frames/000000.jpg",
                "caption": "Shared frame.",
                "alt_text": "Shared frame.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
        ]
    }

    plan = _normalize_frame_selection_plan(payload, outline, frame_manifest)

    assert plan["steps"][0]["selected_frame_path"] == "frames/000000.jpg"
    assert plan["steps"][1]["support_strength"] == "weak"


def test_step_matching_treats_co_thinker_variants_as_equivalent() -> None:
    step = {
        "title": "Start Your Project Planning by Engaging Codex",
        "instruction": "Use Codex as a collaborative partner before coding.",
    }

    assert _step_matches_reference(
        step,
        "Engage Codex as a co-thinker to define project goals.",
    )


def test_final_visual_fit_reassigns_reused_frame_by_step_timing() -> None:
    outline = {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Workflow",
                "goal": "Walk through the lesson",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Design the Project Architecture with Codex",
                        "instruction": "Create the design note.",
                        "text_only_allowed": False,
                    },
                    {
                        "step_id": "step-2",
                        "title": "Download and Prepare YouTube Video Transcripts",
                        "instruction": "Gather transcript input files.",
                        "text_only_allowed": False,
                    },
                ],
            }
        ]
    }
    frame_selection_plan = {
        "schema_version": "1",
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": "frames/000000.jpg",
                "markdown_image_path": "../frames/000000.jpg",
                "caption": "Architecture discussion.",
                "alt_text": "Architecture discussion.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
            {
                "step_id": "step-2",
                "selected_frame_path": "frames/000000.jpg",
                "markdown_image_path": "../frames/000000.jpg",
                "caption": "Transcript input preparation.",
                "alt_text": "Transcript input preparation.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
        ],
    }
    evidence_map = {
        "steps": [
            {"step_id": "step-1", "segment_indexes": [0]},
            {"step_id": "step-2", "segment_indexes": [1]},
        ]
    }
    frame_manifest = {
        "frames": [
            {"image_path": "frames/000000.jpg", "timestamp_seconds": 10.0},
            {"image_path": "frames/000001.jpg", "timestamp_seconds": 120.0},
        ]
    }
    transcript = {
        "segments": [
            {"segment_index": 0, "start_seconds": 8.0},
            {"segment_index": 1, "start_seconds": 118.0},
        ]
    }
    draft_markdown = (
        "### Design the Project Architecture with Codex\n\n"
        "Design the architecture.\n\n"
        "![Architecture discussion.](../frames/000000.jpg)\n\n"
        "*Architecture discussion.*\n\n"
        "### Download and Prepare YouTube Video Transcripts\n\n"
        "Prepare transcript files.\n\n"
        "![Transcript input preparation.](../frames/000000.jpg)\n\n"
        "*Transcript input preparation.*\n"
    )

    refit = _refit_frame_selection_plan_to_draft(
        draft_markdown=draft_markdown,
        outline=outline,
        frame_selection_plan=frame_selection_plan,
        evidence_map=evidence_map,
        frame_manifest=frame_manifest,
        transcript=transcript,
    )

    assert refit["steps"][0]["selected_frame_path"] == "frames/000000.jpg"
    assert refit["steps"][1]["selected_frame_path"] == "frames/000001.jpg"


def test_apply_frame_selection_plan_to_draft_rewrites_section_image_blocks() -> None:
    outline = {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Workflow",
                "goal": "Walk through the lesson",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Download and Prepare YouTube Video Transcripts",
                        "instruction": "Gather transcript input files.",
                        "text_only_allowed": False,
                    }
                ],
            }
        ]
    }
    frame_selection_plan = {
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": "frames/000001.jpg",
                "markdown_image_path": "../frames/000001.jpg",
                "caption": "Transcript input preparation.",
                "alt_text": "Transcript input preparation.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            }
        ]
    }
    draft_markdown = (
        "### Download and Prepare YouTube Video Transcripts\n\n"
        "Prepare transcript files.\n\n"
        "![Old image](../frames/000000.jpg)\n\n"
        "*Old caption.*\n"
    )

    revised = _apply_frame_selection_plan_to_draft(
        draft_markdown,
        outline=outline,
        frame_selection_plan=frame_selection_plan,
    )

    assert "../frames/000001.jpg" in revised
    assert "Transcript input preparation." in revised
    assert "../frames/000000.jpg" not in revised


def test_failure_messages_are_deduplicated_across_reports(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
    agents_dir, skills_dir = _make_agent_files(tmp_path)
    repeated_message = "The opening still reads like project notes."
    llm = FakeTutorialLLM(
        json_responses={
            "tutorial.educator": [_definition()],
            "tutorial.planner": [_outline()],
            "tutorial.evidence": [_evidence()],
            "tutorial.visual": [_visual()],
            "tutorial.technical-review": [
                _technical_review(
                    attention_required=True,
                    findings=[
                        {
                            "severity": "medium",
                            "category": "tutorial_quality",
                            "message": repeated_message,
                            "step_id": "step-1",
                            "reroute_target": "script-writer",
                        }
                    ],
                )
            ],
            "tutorial.adversarial-review": [
                _adversarial_review(
                    attention_required=True,
                    findings=[
                        {
                            "severity": "high",
                            "category": "learner_confusion",
                            "message": repeated_message,
                            "step_id": "step-1",
                            "reroute_target": "script-writer",
                        }
                    ],
                )
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

    assert summary.failures == [repeated_message]


def test_visual_editor_reroute_continues_and_recovers(tmp_path) -> None:
    bundle_path = _make_bundle(tmp_path)
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
                            "support_strength": "weak",
                            "text_only": False,
                            "text_only_reason": None,
                            "notes": "",
                        }
                    ]
                },
                _visual(),
            ],
            "tutorial.technical-review": [_technical_review(), _technical_review()],
            "tutorial.adversarial-review": [
                _adversarial_review(),
                _adversarial_review(),
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

    assert summary.status == "published"
    assert llm.calls.count("tutorial.visual") == 2


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
        (frames_dir / "000001.jpg").write_text("frame", encoding="utf-8")
        frame_manifest = {
            "schema_version": "1",
            "frames": [
                {
                    "frame_index": 0,
                    "timestamp_seconds": 1.0,
                    "timestamp": "00:00:01.000",
                    "image_path": "frames/000000.jpg",
                },
                {
                    "frame_index": 1,
                    "timestamp_seconds": 3.0,
                    "timestamp": "00:00:03.000",
                    "image_path": "frames/000001.jpg",
                },
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
        "source-interpreter.md": (
            "# Agent: source-interpreter\n\n"
            "Skills:\n- tutorial-interpretation\n- grounding\n"
        ),
        "tutorial-planner.md": (
            "# Agent: tutorial-planner\n\n"
            "Skills:\n- tutorial-planning\n- tutorial-step-selection\n"
            "- tutorial-narrative\n- grounding\n"
        ),
        "evidence-mapper.md": (
            "# Agent: evidence-mapper\n\n" "Skills:\n- evidence-mapping\n- grounding\n"
        ),
        "script-writer.md": (
            "# Agent: script-writer\n\nSkills:\n- tutorial-writing\n"
            "- tutorial-narrative\n- public-artifact-hygiene\n"
            "- tutorial-navigation\n- grounding\n"
        ),
        "visual-editor.md": (
            "# Agent: visual-editor\n\nSkills:\n- frame-selection\n- grounding\n"
        ),
        "validator.md": "# Agent: validator\n\nSkills:\n- tutorial-validation\n",
        "technical-reviewer.md": (
            "# Agent: technical-reviewer\n\n"
            "Skills:\n- technical-review\n- tutorial-quality-review\n"
            "- public-artifact-hygiene\n- grounding\n"
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
        "tutorial-interpretation.md": "interpretation",
        "tutorial-step-selection.md": "step selection",
        "tutorial-narrative.md": "narrative",
        "evidence-mapping.md": "evidence",
        "tutorial-writing.md": "writing",
        "public-artifact-hygiene.md": "artifact hygiene",
        "tutorial-navigation.md": "navigation",
        "frame-selection.md": "frames",
        "tutorial-validation.md": "validation",
        "technical-review.md": "tech",
        "tutorial-quality-review.md": "quality review",
        "source-grounding-attack.md": "ground attack",
        "learner-confusion-attack.md": "learner attack",
        "review-response.md": "review response",
    }
    for filename, content in agents.items():
        (agents_dir / filename).write_text(content, encoding="utf-8")
    for filename, content in skills.items():
        (skills_dir / filename).write_text(content, encoding="utf-8")
    return agents_dir, skills_dir


def _definition(**overrides) -> dict[str, object]:
    definition = {
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
        "context_section_required": True,
        "table_of_contents_required": True,
        "back_to_top_links_required": True,
    }
    definition.update(overrides)
    return definition


def _source_interpretation() -> dict[str, object]:
    return {
        "core_workflow": "Run the transcript pipeline and inspect the outputs.",
        "learner_payoff": "Generate transcript artifacts without manual scraping.",
        "best_first_action": "Run the pipeline command against a configured target.",
        "steps_to_emphasize": [
            "Run the pipeline command",
            "Inspect the generated artifacts",
        ],
        "steps_to_demote": [
            "Project folder setup",
            "Recording environment details",
        ],
        "incidental_context": [
            "The video was recorded on a desktop machine.",
        ],
        "terminology_notes": ["Use Codex for the OpenAI coding tool name."],
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


def _outline_with_two_steps() -> dict[str, object]:
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
                        "instruction": "Open the terminal and get ready.",
                        "assumptions": ["A shell is available."],
                        "text_only_allowed": False,
                    },
                    {
                        "step_id": "step-2",
                        "title": "Run the command",
                        "instruction": "Run the command from the video.",
                        "assumptions": ["A shell is available."],
                        "text_only_allowed": False,
                    },
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


def _evidence_with_two_steps() -> dict[str, object]:
    return {
        "steps": [
            {
                "step_id": "step-1",
                "segment_indexes": [0],
                "evidence_strength": "strong",
                "supporting_quote": "Open the terminal.",
                "assumptions": ["A shell is available."],
                "notes": "",
            },
            {
                "step_id": "step-2",
                "segment_indexes": [1],
                "evidence_strength": "strong",
                "supporting_quote": "Run the command.",
                "assumptions": ["A shell is available."],
                "notes": "",
            },
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


def _visual_with_two_steps() -> dict[str, object]:
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
            },
            {
                "step_id": "step-2",
                "selected_frame_path": "frames/000001.jpg",
                "caption": "Command running in the terminal.",
                "alt_text": "Command running in the terminal.",
                "support_strength": "strong",
                "text_only": False,
                "text_only_reason": None,
                "notes": "",
            },
        ]
    }


def _draft_markdown() -> str:
    return (
        '<a id="top"></a>\n\n'
        "# Demo Tutorial\n\n"
        "## What This Tutorial Is For\n\n"
        "This tutorial shows you what the workflow does and what you get from it.\n\n"
        "## Table of Contents\n\n"
        "- [Open the terminal](#open-the-terminal)\n\n"
        '<a id="open-the-terminal"></a>\n\n'
        "## Open the terminal\n\n"
        "Open the terminal and run the command shown in the video.\n\n"
        "![Terminal window prepared for the command.](../frames/000000.jpg)\n\n"
        "*Terminal ready for the command.*\n\n"
        "[Back to top](#top)\n"
    )


def _technical_review(
    *,
    overall_blocked: bool = False,
    attention_required: bool = False,
    findings: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "overall_blocked": overall_blocked,
        "attention_required": attention_required,
        "findings": findings or [],
    }


def _adversarial_review(
    *,
    attention_required: bool = False,
    findings: list[dict[str, object]] | None = None,
    recommended_reroute: str = "script-writer",
) -> dict[str, object]:
    return {
        "source_fidelity_score": 1.0 if not attention_required else 0.6,
        "teachability_score": 1.0 if not attention_required else 0.6,
        "visual_support_score": 1.0 if not attention_required else 0.6,
        "attention_required": attention_required,
        "counter_narrative_summary": "",
        "recommended_reroute": recommended_reroute,
        "findings": findings or [],
    }
