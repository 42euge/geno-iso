"""OpenAI-compatible HTTP API fallback (lazy import).

Works with any service exposing the OpenAI /v1/chat/completions schema
(OpenAI, vLLM, Together, Ollama via /v1, etc.).

Install with: pip install rubric-eval-harness[api]
"""

from __future__ import annotations

import os

from rubric_harness.models.base import GenerationRequest, GenerationResult, ModelClient


class OpenAICompatModel(ModelClient):
    def __init__(
        self,
        model_id: str,
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 60.0,
    ) -> None:
        try:
            import requests  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "api backend requires the 'api' extra: pip install rubric-eval-harness[api]"
            ) from e

        self.name = model_id
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.timeout = timeout

    def generate(self, request: GenerationRequest) -> GenerationResult:
        import requests

        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_new_tokens,
            "temperature": request.temperature,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.stop:
            payload["stop"] = request.stop

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        text = choice["message"]["content"] or ""
        usage = data.get("usage", {})
        return GenerationResult(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            finish_reason=choice.get("finish_reason", "stop"),
            raw={"backend": "openai_compat", "model_id": self.model_id},
        )
