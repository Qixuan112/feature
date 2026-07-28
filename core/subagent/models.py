from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SubAgentConfig:
    subagent_id: str
    name: str
    description: str
    persona: str = ""
    tools: list[str] = field(default_factory=list)
    max_steps: int = 3
    timeout: float = 60.0
