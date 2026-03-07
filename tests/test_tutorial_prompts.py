from __future__ import annotations

from lunduke_transcripts.transforms.tutorial_prompts import (
    build_adversarial_review_prompt,
    build_technical_review_prompt,
    build_writer_prompt,
)


def _definition() -> dict[str, object]:
    return {
        "target_audience": "technical_user",
        "context_section_required": True,
        "table_of_contents_required": True,
        "back_to_top_links_required": True,
    }


def _source_interpretation() -> dict[str, object]:
    return {
        "core_workflow": "Plan and build a transcript pipeline with AI help.",
        "learner_payoff": "Understand the workflow and inspect the outputs.",
        "best_first_action": "Engage the AI assistant to define the goal.",
    }


def _outline() -> dict[str, object]:
    return {
        "sections": [
            {
                "section_id": "section-1",
                "title": "Plan the Project",
                "goal": "Define the workflow before coding.",
                "steps": [
                    {
                        "step_id": "step-1",
                        "title": "Engage the AI Assistant",
                        "instruction": "Define the goal before coding.",
                        "text_only_allowed": False,
                    }
                ],
            }
        ]
    }


def _evidence_map() -> dict[str, object]:
    return {
        "steps": [
            {
                "step_id": "step-1",
                "segment_indexes": [1, 2],
                "evidence_strength": "strong",
                "supporting_quote": "Let's plan together before we code.",
            }
        ]
    }


def _frame_selection_plan() -> dict[str, object]:
    return {
        "steps": [
            {
                "step_id": "step-1",
                "selected_frame_path": "frames/000001.jpg",
                "markdown_image_path": "../frames/000001.jpg",
                "support_strength": "strong",
                "text_only": False,
            }
        ]
    }


def test_writer_prompt_requires_outline_order_and_operational_honesty() -> None:
    prompt = build_writer_prompt(
        definition=_definition(),
        source_interpretation=_source_interpretation(),
        outline=_outline(),
        evidence_map=_evidence_map(),
        frame_selection_plan=_frame_selection_plan(),
        review_feedback=[],
    )

    assert "Follow the section order and step order from the lesson outline." in prompt
    assert "Do not invent exact commands, repo layout details" in prompt
    assert "the walkthrough suggests" in prompt


def test_review_prompts_attack_order_drift_and_false_precision() -> None:
    technical_prompt = build_technical_review_prompt(
        definition=_definition(),
        source_interpretation=_source_interpretation(),
        outline=_outline(),
        evidence_map=_evidence_map(),
        frame_selection_plan=_frame_selection_plan(),
        draft_markdown="# Draft",
        validation_report={"findings": []},
    )
    adversarial_prompt = build_adversarial_review_prompt(
        definition=_definition(),
        source_interpretation=_source_interpretation(),
        outline=_outline(),
        evidence_map=_evidence_map(),
        frame_selection_plan=_frame_selection_plan(),
        draft_markdown="# Draft",
        validation_report={"findings": []},
    )

    assert "Treat draft/outline order drift as a defect" in technical_prompt
    assert (
        "imply runnable precision when the source only demonstrates"
        in adversarial_prompt
    )
