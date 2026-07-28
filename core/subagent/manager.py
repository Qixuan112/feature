from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING

from core.logging_manager import get_logger
from core.agent.agent_executor import AgentExecutor, AgentExecutionContext
from core.agent.tool import ToolSet
from core.prompt_manager import Prompt
from core.provider import LLMRequest
from core.chat.session import Session
from core.chat.message_utils import KiraMessageBatchEvent
from core.adapter.adapter_info import AdapterInfo

from .models import SubAgentConfig

if TYPE_CHECKING:
    from core.provider import ProviderManager
    from core.llm_client import LLMClient

logger = get_logger("subagent", "magenta")

_STUB_ADAPTER = AdapterInfo(
    enabled=True,
    adapter_id="subagent",
    name="subagent",
    platform="subagent",
    description="SubAgent stub adapter",
)


class SubAgentManager:
    """Registers SubAgent configs and executes subagent calls."""

    def __init__(self, provider_mgr: ProviderManager, llm_api: LLMClient):
        self.provider_mgr = provider_mgr
        self.llm_api = llm_api
        self._configs: dict[str, SubAgentConfig] = {}

    def register(self, config: SubAgentConfig) -> bool:
        if not config.subagent_id:
            return False
        self._configs[config.subagent_id] = config
        logger.info(f"Registered SubAgent '{config.subagent_id}'")
        return True

    async def call(
        self,
        subagent_id: str,
        task: str,
        context_summary: str = "",
        timeout: float | None = None,
    ) -> dict:
        config = self._configs.get(subagent_id)
        if not config:
            return {"status": "error", "err": f"SubAgent '{subagent_id}' not found", "result": ""}

        try:
            llm_model = self.provider_mgr.get_default_llm()
        except Exception:
            return {"status": "error", "err": "No default LLM configured", "result": ""}

        tool_set = self._build_tool_set(config)
        agent_executor = AgentExecutor(self.llm_api, tool_set)

        messages = []
        if context_summary:
            messages.append({"role": "system", "content": f"Context from parent conversation:\n{context_summary}"})

        system_prompts = []
        if config.persona:
            system_prompts.append(Prompt(config.persona, name="persona", source="system"))
        system_prompts.append(Prompt(
            "You are a specialized sub-agent. Focus on the assigned task and respond concisely. "
            "Return your final answer directly without extra meta-commentary.",
            name="subagent_role",
            source="system",
        ))

        llm_request = LLMRequest(messages=messages, tool_set=tool_set)
        llm_request.system_prompt.extend(system_prompts)
        llm_request.user_prompt.append(Prompt(task, name="task", source="user"))
        llm_request.assemble_prompt()

        cid = f"sub_{uuid.uuid4().hex[:12]}"
        stub_event = KiraMessageBatchEvent(
            message_types=[],
            timestamp=int(time.time()),
            session=Session(adapter_name="subagent", session_type="dm", session_id=cid),
            adapter=_STUB_ADAPTER,
        )

        agent_ctx = AgentExecutionContext(
            event=stub_event,
            request=llm_request,
            new_messages=[],
            model_group=[llm_model],
        )

        async def _run():
            final_text = ""
            async for step in agent_executor.run(agent_ctx, max_steps=config.max_steps):
                resp = step.llm_response
                if not resp:
                    break
                if resp.text_response:
                    final_text = resp.text_response
                if step.state == "error":
                    return {"status": "error", "err": step.err or "Agent error", "result": final_text}
                if not step.has_tool_calls or step.is_final:
                    break
            return {"status": "success", "result": final_text}

        start = time.time()
        try:
            result = await asyncio.wait_for(_run(), timeout=timeout or config.timeout)
            result["time_consumed"] = round(time.time() - start, 3)
            return result
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "err": f"SubAgent '{subagent_id}' timed out after {timeout or config.timeout}s",
                "result": "",
                "time_consumed": round(time.time() - start, 3),
            }
        except Exception as e:
            logger.error(f"SubAgent '{subagent_id}' error: {e}")
            return {"status": "error", "err": str(e), "result": "", "time_consumed": round(time.time() - start, 3)}

    def _build_tool_set(self, config: SubAgentConfig) -> ToolSet:
        if not config.tools:
            return ToolSet()
        allowed = set(config.tools) - {"call_subagent"}
        full_set = self.llm_api.build_tool_set()
        tool_set = ToolSet()
        for tool in full_set.tools:
            if tool.name in allowed:
                tool_set.add(tool)
        return tool_set
