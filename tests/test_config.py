import pytest

from open_data_scientist.utils.config import validate_runtime_config


def test_rejects_tci_with_openai_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    with pytest.raises(ValueError, match="only compatible with provider 'together'"):
        validate_runtime_config(provider="openai", executor="tci", model="gpt-4o-mini")


def test_requires_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        validate_runtime_config(provider="openai", executor="internal", model="gpt-4o-mini")
