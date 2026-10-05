"""Generic Google Gemini chat model wrapper."""

import os
from functools import lru_cache
from typing import Any, Mapping
from langsmith import traceable
from langchain_google_genai import ChatGoogleGenerativeAI


class LLM:
    """Create Gemini chat models from configuration and invoke them with a prompt."""

    def __init__(
        self,
        config_payload: Mapping[str, Any] | None = None,
        model: str | None = None,
    ) -> None:
        self.config_payload = dict(config_payload or {})
        self.model = model or os.getenv("GEMINI_MODEL", "models/gemini-3.8-flash")
        self._client: ChatGoogleGenerativeAI | None = None

    def _model_config(self) -> dict[str, Any]:
        payload = dict(self.config_payload)
        models = payload.pop("models", None)
        if isinstance(models, Mapping):
            model_config = models.get(self.model)
            if isinstance(model_config, Mapping):
                payload.update(model_config)
            # Missing or invalid model-specific config is simply omitted.

        nested = payload.pop("config", None)
        if isinstance(nested, Mapping):
            payload.update(nested)
        payload.pop("model", None)
        payload.pop("provider", None)

        api_key = payload.pop("google_api_key", None) or os.getenv("GEMINI_API_KEY")
        if api_key:
            payload["google_api_key"] = api_key

        payload.setdefault("temperature", 0.2)
        payload.setdefault("timeout", 60)
        payload.setdefault("max_retries", 2)
        return payload

    def _get_client(self) -> ChatGoogleGenerativeAI:
        if self._client is None:
            self._client = ChatGoogleGenerativeAI(model=self.model, **self._model_config())
        return self._client

    @staticmethod
    def _to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, str):
                    parts.append(p)
                elif isinstance(p, dict) and p.get("type", "text") == "text":
                    parts.append(p.get("text", ""))
            return "".join(parts)
        return str(content)

    @traceable(run_type="llm", name="LLM")
    def llm_call(self, prompt: str) -> str:
        """Blocking call: returns the response text."""
        return self._to_text(self._get_client().invoke(prompt).content)

    async def allm_call(self, prompt: str) -> str:
        """Async call for use inside FastAPI endpoints."""
        response = await self._get_client().ainvoke(prompt)
        return self._to_text(response.content)


@lru_cache(maxsize=1)
def _default_llm() -> LLM:
    return LLM()


def llm_call(prompt: str) -> str:
    """Convenience call using default Gemini settings."""
    return _default_llm().llm_call(prompt)


async def allm_call(prompt: str) -> str:
    return await _default_llm().allm_call(prompt)