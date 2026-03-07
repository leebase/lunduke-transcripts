"""Agent and skill loading for the tutorial pipeline."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


def _sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SkillSpec:
    """Loaded tutorial skill definition."""

    name: str
    path: Path
    body: str
    digest: str


@dataclass(frozen=True)
class AgentSpec:
    """Loaded tutorial agent definition and referenced skills."""

    name: str
    path: Path
    body: str
    skills: list[SkillSpec]
    digest: str

    @property
    def skill_names(self) -> list[str]:
        return [skill.name for skill in self.skills]


class TutorialAgentRegistry:
    """Loads repo-local agent role files and tutorial skills."""

    def __init__(self, *, agents_dir: Path, skills_dir: Path) -> None:
        self.agents_dir = agents_dir
        self.skills_dir = skills_dir

    def load(self, agent_name: str) -> AgentSpec:
        agent_path = self.agents_dir / f"{agent_name}.md"
        if not agent_path.exists():
            raise RuntimeError(f"tutorial_agent_missing: {agent_path}")
        body = agent_path.read_text(encoding="utf-8")
        skill_names = _parse_skill_names(body)
        skills = [self._load_skill(skill_name) for skill_name in skill_names]
        combined = body + "".join(skill.body for skill in skills)
        return AgentSpec(
            name=agent_name,
            path=agent_path,
            body=body,
            skills=skills,
            digest=_sha1_text(combined),
        )

    def manifest_entry(self, agent_name: str) -> dict[str, object]:
        agent = self.load(agent_name)
        return {
            "name": agent.name,
            "path": str(agent.path),
            "digest": agent.digest,
            "skills": [
                {
                    "name": skill.name,
                    "path": str(skill.path),
                    "digest": skill.digest,
                }
                for skill in agent.skills
            ],
        }

    def _load_skill(self, skill_name: str) -> SkillSpec:
        skill_path = self.skills_dir / f"{skill_name}.md"
        if not skill_path.exists():
            raise RuntimeError(f"tutorial_skill_missing: {skill_path}")
        body = skill_path.read_text(encoding="utf-8")
        return SkillSpec(
            name=skill_name,
            path=skill_path,
            body=body,
            digest=_sha1_text(body),
        )


def _parse_skill_names(body: str) -> list[str]:
    lines = body.splitlines()
    collecting = False
    skill_names: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "Skills:":
            collecting = True
            continue
        if collecting and stripped.startswith("- "):
            skill_names.append(stripped.removeprefix("- ").strip())
            continue
        if collecting and stripped:
            break
    return skill_names
