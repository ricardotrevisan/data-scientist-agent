from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
import os


def _load_env_file() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


class LLMProvider(Protocol):
    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_output_tokens: int,
        timeout: int,
    ) -> str:
        ...


@dataclass
class OpenAIProvider:
    client_config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        _load_env_file()

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is not installed. Install dependency 'openai'."
            ) from exc

        kwargs: dict[str, Any] = {}
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        if self.client_config:
            kwargs.update(self.client_config)

        self._client = OpenAI(**kwargs)
        return self._client

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_output_tokens: int,
        timeout: int,
    ) -> str:
        client = self._get_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_output_tokens,
            "timeout": timeout,
            "stream": False,
        }
        # Avoid sending temperature=0.0 to models/endpoints that reject it.
        if temperature and temperature > 0:
            payload["temperature"] = temperature

        try:
            response = client.chat.completions.create(**payload)
            return response.choices[0].message.content or ""
        except Exception as exc:
            # Single compatibility fallback: some endpoints expect max_tokens.
            err_text = str(exc).lower()
            if "max_completion_tokens" not in err_text:
                raise
            payload.pop("max_completion_tokens", None)
            payload["max_tokens"] = max_output_tokens
            response = client.chat.completions.create(**payload)
            return response.choices[0].message.content or ""


@dataclass
class TogetherProvider:
    client_config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        _load_env_file()

        try:
            from together import Client
        except ImportError as exc:
            raise RuntimeError(
                "Together SDK not installed. Install optional dependency with: pip install 'open-data-scientist[together]'"
            ) from exc

        kwargs = self.client_config or {}
        self._client = Client(**kwargs)
        return self._client

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_output_tokens: int,
        timeout: int,
    ) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_output_tokens,
            timeout=timeout,
            stream=False,
        )
        return response.choices[0].message.content or ""


def create_llm_provider(
    provider: str = "openai", client_config: dict[str, Any] | None = None
) -> LLMProvider:
    normalized = provider.lower()
    if normalized == "openai":
        return OpenAIProvider(client_config=client_config)
    if normalized == "together":
        return TogetherProvider(client_config=client_config)
    raise ValueError(
        f"Unsupported provider '{provider}'. Supported providers: openai, together"
    )
