"""call_subagent tool: lets the main agent delegate tasks to registered sub-agents."""
from __future__ import annotations

from core.utils.tool_utils import BaseTool

if TYPE_CHECKING:
    from core.subagent.manager import SubAgentManager

from typing import TYPE_CHECKING


class CallSubAgentTool(BaseTool):
    name = "call_subagent"
    description = (
        "调用一个已注册的子代理(subagent)完成子任务。"
        "子代理拥有独立的角色设定和工具集，会自主完成任务并返回结果。"
        "适用于代码审查、深度分析、翻译等需要专业能力的子任务。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "subagent_id": {"type": "string", "description": "子代理ID，例如 'code_expert'"},
            "task": {"type": "string", "description": "需要完成的具体任务描述"},
        },
        "required": ["subagent_id", "task"],
    }

    def __init__(self, manager: SubAgentManager):
        super().__init__()
        self.manager = manager

    async def execute(self, event, **kwargs) -> str:
        subagent_id = kwargs.get("subagent_id", "")
        task = kwargs.get("task", "")
        if not subagent_id or not task:
            return "Error: 'subagent_id' and 'task' are required."

        result = await self.manager.call(subagent_id=subagent_id, task=task)
        if result["status"] == "success":
            return f"SubAgent '{subagent_id}' result:\n{result['result']}"
        return f"Error: SubAgent '{subagent_id}' {result['status']}: {result.get('err', '')}"
