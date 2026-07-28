from core.subagent.models import SubAgentConfig

CODE_EXPERT = SubAgentConfig(
    subagent_id="code_expert",
    name="代码专家",
    description="擅长编写、审查、重构和解释代码",
    persona=(
        "你是一位资深软件工程师，擅长代码审查、Bug 定位、重构和技术方案评估。"
        "优先给出可运行的代码示例，指出潜在风险，保持代码风格一致。"
    ),
    tools=["read_file", "write_file"],
    max_steps=5,
    timeout=120.0,
)

BUILTIN_SUBAGENTS = [CODE_EXPERT]
