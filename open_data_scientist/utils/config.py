from __future__ import annotations

import os


def load_env_file() -> None:
    """Load environment variables from a local .env file when available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def validate_runtime_config(provider: str, executor: str, model: str) -> None:
    load_env_file()
    provider_norm = provider.lower()
    executor_norm = executor.lower()

    if provider_norm not in {"openai", "together"}:
        raise ValueError(
            f"Unsupported provider '{provider}'. Supported providers: openai, together"
        )

    if executor_norm not in {"internal", "tci"}:
        raise ValueError(
            f"Unsupported executor '{executor}'. Supported executors: internal, tci"
        )

    if executor_norm == "tci" and provider_norm != "together":
        raise ValueError(
            "Executor 'tci' is only compatible with provider 'together'. "
            "Use '--provider together --executor tci' or switch to '--executor internal'."
        )

    if provider_norm == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Set it with: export OPENAI_API_KEY='your-api-key-here'"
        )

    if provider_norm == "together" and not os.getenv("TOGETHER_API_KEY"):
        raise ValueError(
            "TOGETHER_API_KEY environment variable not set. "
            "Set it with: export TOGETHER_API_KEY='your-api-key-here'"
        )

    if provider_norm == "openai" and "/" in model:
        # Heuristic warning-as-error to avoid silent model/provider mismatch.
        raise ValueError(
            f"Model '{model}' looks Together/HF-style. "
            "Use an OpenAI model id like 'gpt-5-mini' when provider is openai."
        )
