import os

from open_data_scientist.utils.strings import sanitize_filename
from open_data_scientist.utils.strings import PROMPT_TEMPLATE
from open_data_scientist.utils.llm_providers import create_llm_provider
from open_data_scientist.utils.config import load_env_file

def _format_history(history):
    """Format history messages into a readable summary"""
    if not history:
        return "No previous conversation history."
    
    formatted_parts = []
    
    for i, message in enumerate(history, 1):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        formatted_parts.append(f"{i}. {role}: {content}")
    
    return "\n\n".join(formatted_parts)


def _write_report(
    user_input,
    result,
    history,
    model=None,
    provider="openai",
    client_config=None,
    temperature=0.3,
    max_output_tokens=2000,
    timeout=120,
):
    """Write the report to a file"""
    load_env_file()
    resolved_model = model or os.getenv("ODS_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5-mini"
    llm_provider = create_llm_provider(provider=provider, client_config=client_config)

    formatted_history = _format_history(history)

    output_report = llm_provider.generate(
        model=resolved_model,
        messages=[
            {"role": "system", "content": PROMPT_TEMPLATE["REPORT_WRITER"]},
            {
                "role": "user",
                "content": f"Conversation History:\n{formatted_history}\n\nUser input: {user_input}\nFinal result: {result}",
            },
        ],
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        timeout=timeout,
    )

    report_name = f"report-{sanitize_filename(user_input)}.md"
    
    with open(report_name, "w") as f:
        f.write(output_report)
    
