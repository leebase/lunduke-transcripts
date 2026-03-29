"""Prompt builders for the multi-agent tutorial pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lunduke_transcripts.app.tutorial_agent_registry import AgentSpec


def build_system_prompt(agent: AgentSpec) -> str:
    """Compose one system prompt from the agent role and its skills."""

    parts = [agent.body.strip()]
    for skill in agent.skills:
        parts.append(f"Skill: {skill.name}\n{skill.body.strip()}")
    return "\n\n".join(part for part in parts if part).strip() + "\n"


def build_educator_prompt(
    *,
    bundle: dict[str, Any],
    transcript: dict[str, Any],
    frame_manifest: dict[str, Any] | None,
) -> str:
    return _prompt_with_json(
        title="Create the tutorial definition of done.",
        sections={
            "Source bundle": bundle,
            "Transcript summary": {
                "title": transcript.get("title"),
                "language": transcript.get("language"),
                "transcript_source": transcript.get("transcript_source"),
                "segment_count": len(transcript.get("segments", [])),
                "segments_preview": transcript.get("segments", [])[:8],
                "frame_count": len((frame_manifest or {}).get("frames", [])),
            },
        },
        instructions=[
            "Return JSON only.",
            "Audience defaults to a technical user.",
            "Allowed enrichment must be `light`.",
            "First output target must be `markdown`.",
            (
                "Prefer prerequisites that are explicitly shown or minimally "
                "required. Do not list machine-specific environments like a "
                "Mac Mini, Git fluency, API keys, or architecture concepts as "
                "global prerequisites unless the source makes them clearly necessary."
            ),
            (
                "Do not describe the final tutorial as a step-by-step or "
                "copy-paste guide when the source only demonstrates a workflow "
                "pattern."
            ),
            (
                "If the source demonstrates a workflow without full runnable "
                "commands, frame learning objectives and success criteria around "
                "understanding or following the demonstrated workflow, not full "
                "copy-paste reproduction."
            ),
            "The final tutorial must include context before instruction begins.",
            (
                "The final tutorial must include a table of contents and "
                "section navigation."
            ),
            "Unsupported factual claims must be treated as high-priority issues.",
            (
                "Weak visual support must be treated as a high-priority issue "
                "unless a step is explicitly text-only."
            ),
        ],
        schema={
            "target_audience": "technical_user",
            "learning_objectives": ["..."],
            "prerequisites": ["..."],
            "success_criteria": ["..."],
            "allowed_enrichment_level": "light",
            "evidence_requirements": {
                "transcript_support_required": True,
                "unsupported_factual_claims_block": True,
            },
            "visual_requirements": {
                "weak_visual_support_blocks": True,
                "text_only_requires_justification": True,
            },
            "blocking_conditions": ["..."],
            "output_targets": ["markdown"],
            "context_section_required": True,
            "table_of_contents_required": True,
            "back_to_top_links_required": True,
        },
    )


def build_planner_prompt(
    *,
    definition: dict[str, Any],
    source_interpretation: dict[str, Any],
    transcript: dict[str, Any],
    feedback: list[str],
) -> str:
    return _prompt_with_json(
        title="Plan the tutorial structure from the definition and transcript.",
        sections={
            "Tutorial definition": definition,
            "Source interpretation": source_interpretation,
            "Transcript segments": transcript.get("segments", []),
            "Review feedback": feedback,
        },
        instructions=[
            "Return JSON only.",
            "Create 2-6 sections with ordered steps for a public-facing tutorial.",
            (
                "The first section should explain what the tutorial is for "
                "and what the reader will get from it."
            ),
            (
                "Keep that opening context compact. Do not turn generic "
                "`why this matters`, `by the end`, or broad motivational copy "
                "into separate outline steps unless the transcript clearly "
                "supports them as distinct taught material."
            ),
            (
                "Use at most one compact orientation step in the opening "
                "section unless the source clearly teaches prerequisites or "
                "setup as distinct lesson material."
            ),
            "Each step must include a stable `step_id`.",
            (
                "Only create steps that can be grounded in transcript evidence. "
                "Do not add speculative extension guidance, future roadmap "
                "ideas, or generic next-step advice unless the source "
                "explicitly demonstrates them."
            ),
            "Flag assumptions and prerequisites that matter to execution.",
            (
                "Keep assumptions minimal and evidence-based. Avoid assumptions "
                "like ChatGPT Plus, architecture fluency, sprint-planning "
                "knowledge, or API-key setup unless the source clearly makes "
                "them necessary."
            ),
            (
                "Do not turn incidental environment details into tutorial "
                "steps unless they are required for the workflow."
            ),
            "Prefer learner order over transcript chronology when the video rambles.",
            (
                "Start the first actionable section with the core workflow, "
                "not remote access, recording setup, machine names, or "
                "one-off environment context unless those are truly required."
            ),
            (
                "Demote incidental setup into prerequisites or brief context "
                "when the learner can succeed without treating it as a core step."
            ),
            (
                "Prefer the first irreversible workflow action over scaffolding "
                "steps like creating folders, opening remote sessions, or "
                "describing the recording environment."
            ),
            (
                "Make the first actionable section align with `best_first_action` "
                "from the source interpretation unless review feedback explicitly "
                "says that interpretation was wrong."
            ),
            (
                "Do not promote anything listed under `steps_to_demote` into a "
                "core tutorial step unless the workflow would fail without it."
            ),
        ],
        schema={
            "sections": [
                {
                    "section_id": "section-1",
                    "title": "...",
                    "goal": "...",
                    "steps": [
                        {
                            "step_id": "step-1",
                            "title": "...",
                            "instruction": "...",
                            "assumptions": ["..."],
                            "text_only_allowed": False,
                        }
                    ],
                }
            ]
        },
    )


def build_source_interpretation_prompt(
    *,
    definition: dict[str, Any],
    transcript: dict[str, Any],
    feedback: list[str],
) -> str:
    return _prompt_with_json(
        title="Interpret what this source should teach before planning the tutorial.",
        sections={
            "Tutorial definition": definition,
            "Transcript segments": transcript.get("segments", []),
            "Review feedback": feedback,
        },
        instructions=[
            "Return JSON only.",
            (
                "Identify the real workflow the learner came to understand, "
                "not a chronological recap of everything shown on screen."
            ),
            (
                "Separate core workflow actions from incidental setup, "
                "recording context, machine-specific details, and project "
                "scaffolding."
            ),
            (
                "Call out the best first actionable move for the learner once "
                "basic context is established."
            ),
            (
                "The `best_first_action` must be a core workflow move, not "
                "creating folders, naming files, opening remote sessions, or "
                "other setup scaffolding unless the source is explicitly a "
                "setup tutorial."
            ),
            (
                "If the source includes AI/tool-name homophones such as "
                "`codecs` where `Codex` is clearly intended, normalize them."
            ),
        ],
        schema={
            "core_workflow": "...",
            "learner_payoff": "...",
            "best_first_action": "...",
            "steps_to_emphasize": ["..."],
            "steps_to_demote": ["..."],
            "incidental_context": ["..."],
            "terminology_notes": ["..."],
        },
    )


def build_evidence_prompt(
    *,
    definition: dict[str, Any],
    source_interpretation: dict[str, Any],
    outline: dict[str, Any],
    transcript: dict[str, Any],
    feedback: list[str],
) -> str:
    return _prompt_with_json(
        title="Map each tutorial step to transcript evidence.",
        sections={
            "Tutorial definition": definition,
            "Source interpretation": source_interpretation,
            "Lesson outline": outline,
            "Transcript segments": transcript.get("segments", []),
            "Review feedback": feedback,
        },
        instructions=[
            "Return JSON only.",
            "Every step must map to transcript segment indexes.",
            "Use `weak` evidence strength if the support is thin or implied.",
        ],
        schema={
            "steps": [
                {
                    "step_id": "step-1",
                    "segment_indexes": [0, 1],
                    "evidence_strength": "strong",
                    "supporting_quote": "...",
                    "assumptions": ["..."],
                    "notes": "...",
                }
            ]
        },
    )


def build_visual_prompt(
    *,
    definition: dict[str, Any],
    source_interpretation: dict[str, Any],
    outline: dict[str, Any],
    evidence_map: dict[str, Any],
    frame_manifest: dict[str, Any] | None,
    tutorial_dir: Path,
    feedback: list[str],
) -> str:
    frames = (frame_manifest or {}).get("frames", [])
    return _prompt_with_json(
        title="Select the best frame for each tutorial step.",
        sections={
            "Tutorial definition": definition,
            "Source interpretation": source_interpretation,
            "Lesson outline": outline,
            "Evidence map": evidence_map,
            "Frame candidates": frames,
            "Tutorial dir": {"relative_image_base": str(tutorial_dir)},
            "Review feedback": feedback,
        },
        instructions=[
            "Return JSON only.",
            "Each step must either choose one frame or mark the step as text-only.",
            (
                "If no frame is suitable, set `text_only` to true and provide "
                "`text_only_reason`."
            ),
            "Use the original frame path from the manifest, not a copied path.",
        ],
        schema={
            "steps": [
                {
                    "step_id": "step-1",
                    "selected_frame_path": "frames/000000.jpg",
                    "caption": "...",
                    "alt_text": "...",
                    "support_strength": "strong",
                    "text_only": False,
                    "text_only_reason": None,
                    "notes": "...",
                }
            ]
        },
    )


def build_writer_prompt(
    *,
    definition: dict[str, Any],
    source_interpretation: dict[str, Any],
    outline: dict[str, Any],
    evidence_map: dict[str, Any],
    frame_selection_plan: dict[str, Any],
    review_feedback: list[str],
) -> str:
    return _prompt_with_markdown(
        title="Write the tutorial draft in Markdown only.",
        sections={
            "Tutorial definition": definition,
            "Source interpretation": source_interpretation,
            "Lesson outline": outline,
            "Evidence map": evidence_map,
            "Frame selection plan": frame_selection_plan,
            "Review feedback": review_feedback,
        },
        instructions=[
            "Write only Markdown. Do not wrap it in code fences.",
            "Stay grounded in the evidence map.",
            "Sound like the speaker in the video if coached by a top-notch educator.",
            (
                "Follow the section order and step order from the lesson outline. "
                "Do not reorder steps unless review feedback explicitly told you "
                "to change the outline."
            ),
            (
                "Represent each outline step title clearly in the draft and keep "
                "the wording close enough that a reviewer can match the draft back "
                "to the outline."
            ),
            (
                "Use light enrichment for orientation, framing, and concise "
                "practical clarity."
            ),
            'Start with `<a id="top"></a>` on its own line.',
            (
                "Include a `## What This Tutorial Is For` section before the "
                "tutorial steps."
            ),
            (
                "Explain what the tutorial accomplishes, why it matters, and "
                "what the reader will understand or be able to inspect by the "
                "end before the workflow sections begin."
            ),
            (
                "Keep that opening context compact. Do not create a separate "
                "`What You Will Have by the End` or similar intro subsection "
                "unless the source clearly teaches it as a distinct part of "
                "the lesson."
            ),
            (
                "Make the opening context sound public-facing and learner-oriented, "
                "not like project notes or a transcript summary."
            ),
            "Include a `## Table of Contents` section with internal links.",
            (
                "Do not make remote-access details, machine names, recording "
                "setup, or other incidental environment context the first "
                "actionable step unless the workflow truly depends on them."
            ),
            (
                "If setup context matters but is not core to the lesson, keep "
                "it brief in the intro or prerequisites instead of turning it "
                "into a main tutorial step."
            ),
            (
                "Do not create top-level sections about source limitations, "
                "visual notes, evidence posture, or other production scaffolding. "
                "If a caveat is essential, weave it into the relevant intro or step."
            ),
            (
                "Favor payoff-oriented section titles and sequencing that help "
                "the reader complete the workflow, not a play-by-play of what "
                "happened on screen."
            ),
            (
                "Treat the source as a demonstrated workflow, not proof of product "
                "capabilities beyond what the transcript evidence actually supports."
            ),
            (
                "If the source does not support full independent reproduction, "
                "say so once in the opening scope note and keep the rest of the "
                "tutorial focused on the workflow pattern rather than repeating "
                "the same caveat in every section."
            ),
            (
                "Do not invent exact commands, repo layout details, prerequisites, "
                "or output guarantees. If the source does not show them concretely, "
                "say that this screencast demonstrates the workflow at a higher level."
            ),
            (
                "Do not present machine-specific context such as a Mac Mini, an "
                "already-created folder, or a personal workflow label as a core "
                "prerequisite unless the tutorial would fail without it."
            ),
            (
                "When the evidence is suggestive rather than definitive, use "
                "careful language such as `the walkthrough suggests`, `the example "
                "shows`, or `the demonstrated project uses` instead of presenting "
                "the claim as a guaranteed product fact."
            ),
            (
                "Do not turn a missing operational detail into smooth filler prose. "
                "Either ground the detail in evidence or acknowledge that the source "
                "does not provide an exact command or configuration."
            ),
            (
                "When you describe sprint execution, do not imply Codex can run "
                "the whole build autonomously or flawlessly. Keep the human in "
                "the loop for inspection, manual testing, and follow-up fixes."
            ),
            (
                "When you describe transcript inputs, make the minimum input "
                "shape explicit at a high level. If the source does not show a "
                "full schema, say that the workflow is operating on raw "
                "transcript text plus whatever metadata the project already has, "
                "rather than inventing a strict file format."
            ),
            (
                "For each workflow subsection, give the learner one concrete "
                "outcome to carry forward, such as a product definition, "
                "design note, sprint plan, review findings, or progress "
                "tracker entry, but only when that artifact or decision is "
                "clearly supported by the source."
            ),
            (
                "Every major section after the table of contents must end "
                "with `[Back to top](#top)`."
            ),
            (
                "Do not include evidence sections, supporting quotes, "
                "transcript citations, or reviewer/provenance language in "
                "the final Markdown."
            ),
            (
                "Preserve exact tool and product names. Do not autocorrect or "
                "silently rename names like `Codex`."
            ),
            (
                "Correct obvious transcript or ASR homophone mistakes in tool "
                "names when the intended product is clear, such as using "
                "`Codex` instead of `codecs` for the OpenAI coding tool."
            ),
            "Do not write `Evidence:` anywhere in the tutorial.",
            (
                "Do not narrate the video with phrases like `the speaker "
                "says` unless absolutely necessary."
            ),
            "Include images with standard Markdown when a frame is selected.",
            (
                "Use the frame path relative to the tutorial directory, such as "
                "`../frames/000000.jpg`."
            ),
            (
                "If an image is included, you may add a short italic "
                "caption, but do not add evidence callouts."
            ),
        ],
    )


def build_technical_review_prompt(
    *,
    definition: dict[str, Any],
    source_interpretation: dict[str, Any],
    outline: dict[str, Any],
    evidence_map: dict[str, Any],
    frame_selection_plan: dict[str, Any],
    draft_markdown: str,
    validation_report: dict[str, Any],
) -> str:
    return _prompt_with_json(
        title="Review the tutorial draft like a technical reviewer.",
        sections={
            "Tutorial definition": definition,
            "Source interpretation": source_interpretation,
            "Lesson outline": outline,
            "Evidence map": evidence_map,
            "Frame selection plan": frame_selection_plan,
            "Validation report": validation_report,
            "Draft markdown": draft_markdown,
        },
        instructions=[
            "Return JSON only.",
            (
                "Focus on technical accuracy, completeness, sequence quality, "
                "operational usability, and whether this works as a public tutorial."
            ),
            (
                "Treat a weak opening payoff, project-note voice, or an "
                "incidental setup-first lesson structure as tutorial-quality defects."
            ),
            (
                "Treat draft/outline order drift as a defect when the draft "
                "reorders steps in a way that changes learner sequencing."
            ),
            (
                "Treat transcript leakage, missing context, missing table "
                "of contents, and internal-thinking leakage as "
                "tutorial-quality defects."
            ),
            (
                "Treat obvious tool-name mistakes, such as `codecs` where "
                "`Codex` is clearly intended, as copy-edit defects that must "
                "be corrected in the next pass, but only report this if the "
                "draft itself literally contains `codecs` or another wrong form."
            ),
            "Call out incidental setup steps that do not belong in the core tutorial.",
            (
                "If the first actionable step is just remote access, machine "
                "setup, or recording context, call that out as a structural problem."
            ),
            "Do not rewrite the draft. Report findings only.",
            (
                "Each finding must include `severity`, `category`, "
                "`message`, and `reroute_target`."
            ),
            (
                "Set `attention_required` when the draft needs another pass, "
                "but do not act like a publish gate."
            ),
        ],
        schema={
            "attention_required": False,
            "findings": [
                {
                    "severity": "medium",
                    "category": "completeness",
                    "message": "...",
                    "step_id": "step-1",
                    "reroute_target": "script-writer",
                }
            ],
        },
    )


def build_adversarial_review_prompt(
    *,
    definition: dict[str, Any],
    source_interpretation: dict[str, Any],
    outline: dict[str, Any],
    evidence_map: dict[str, Any],
    frame_selection_plan: dict[str, Any],
    draft_markdown: str,
    validation_report: dict[str, Any],
) -> str:
    return _prompt_with_json(
        title="Adversarially attack this tutorial draft.",
        sections={
            "Tutorial definition": definition,
            "Source interpretation": source_interpretation,
            "Lesson outline": outline,
            "Evidence map": evidence_map,
            "Frame selection plan": frame_selection_plan,
            "Validation report": validation_report,
            "Draft markdown": draft_markdown,
        },
        instructions=[
            "Return JSON only.",
            (
                "Attack unsupported claims, transcript meaning drift, learner "
                "confusion, and weak screenshot support."
            ),
            (
                "Attack drafts that read like internal project notes, bury the "
                "real payoff, or start the lesson with incidental setup instead "
                "of the workflow the reader came to learn."
            ),
            (
                "Attack drafts that imply runnable precision when the source only "
                "demonstrates a workflow at a conceptual level."
            ),
            "You are advisory only. You do not decide publishability.",
            (
                "Inject a counter-narrative and pressure-test overreach, "
                "but do not veto release."
            ),
            (
                "Flag voice drift, evidence leakage, generic tutorial "
                "prose, and internal scaffolding leaking into the public "
                "artifact."
            ),
            (
                "Flag obvious tool-name or product-name mistakes when the "
                "draft preserves a transcript homophone instead of the "
                "intended term, such as `codecs` for `Codex`, but only if the "
                "draft text literally contains that wrong term."
            ),
            "Do not rewrite the tutorial.",
            (
                "Each finding must include `severity`, `category`, "
                "`message`, and `reroute_target`."
            ),
        ],
        schema={
            "source_fidelity_score": 1.0,
            "teachability_score": 1.0,
            "visual_support_score": 1.0,
            "attention_required": False,
            "counter_narrative_summary": "...",
            "recommended_reroute": "script-writer",
            "findings": [
                {
                    "severity": "high",
                    "category": "source_fidelity",
                    "message": "...",
                    "step_id": "step-1",
                    "reroute_target": "evidence-mapper",
                }
            ],
        },
    )


def _prompt_with_json(
    *,
    title: str,
    sections: dict[str, Any],
    instructions: list[str],
    schema: dict[str, Any],
) -> str:
    lines = [title, ""]
    for heading, payload in sections.items():
        lines.append(f"{heading}:")
        lines.append(json.dumps(payload, indent=2, sort_keys=True))
        lines.append("")
    lines.append("Instructions:")
    for instruction in instructions:
        lines.append(f"- {instruction}")
    lines.append("")
    lines.append("Return JSON with this shape:")
    lines.append(json.dumps(schema, indent=2, sort_keys=True))
    return "\n".join(lines).strip() + "\n"


def _prompt_with_markdown(
    *,
    title: str,
    sections: dict[str, Any],
    instructions: list[str],
) -> str:
    lines = [title, ""]
    for heading, payload in sections.items():
        lines.append(f"{heading}:")
        if isinstance(payload, str):
            lines.append(payload)
        else:
            lines.append(json.dumps(payload, indent=2, sort_keys=True))
        lines.append("")
    lines.append("Instructions:")
    for instruction in instructions:
        lines.append(f"- {instruction}")
    return "\n".join(lines).strip() + "\n"
