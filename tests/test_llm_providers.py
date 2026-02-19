from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import pytest

from open_data_scientist.utils.llm_providers import (
    OpenAIProvider,
    TogetherProvider,
    create_llm_provider,
)


def test_openai_provider_generate():
    content = "hello from openai"
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    response = SimpleNamespace(choices=[choice])

    client = MagicMock()
    client.chat.completions.create.return_value = response

    provider = OpenAIProvider()
    provider._client = client
    result = provider.generate(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=100,
        timeout=30,
    )
    assert result == content


def test_provider_factory_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported provider"):
        create_llm_provider("unknown")


def test_together_provider_import_error_message():
    provider = TogetherProvider()
    with patch.dict("sys.modules", {"together": None}):
        with pytest.raises(RuntimeError, match="Together SDK not installed"):
            provider._get_client()
