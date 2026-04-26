"""Build a ModelClient from a config dict.

Example config snippets:

    backend: mock
    name: judge-mock

    backend: hf
    model_id: Qwen/Qwen2.5-0.5B-Instruct
    device: cuda

    backend: llama_cpp
    model_path: /models/qwen2.5-0.5b-instruct-q4.gguf
    n_ctx: 4096

    backend: openai
    model_id: gpt-4o-mini
    base_url: https://api.openai.com/v1
    api_key_env: OPENAI_API_KEY
"""

from __future__ import annotations

from typing import Any

from rubric_harness.models.base import ModelClient
from rubric_harness.models.mock import MockModel


def build_model(config: dict[str, Any] | None) -> ModelClient:
    if not config:
        return MockModel()

    backend = config.get("backend", "mock").lower()

    if backend == "mock":
        return MockModel(
            name=config.get("name", "mock"),
            default_seed=config.get("default_seed", 0),
        )

    if backend in {"hf", "huggingface", "transformers"}:
        from rubric_harness.models.hf import HFModel

        return HFModel(
            model_id=config["model_id"],
            device=config.get("device"),
            dtype=config.get("dtype", "auto"),
            trust_remote_code=config.get("trust_remote_code", False),
        )

    if backend in {"llama_cpp", "llamacpp", "llama"}:
        from rubric_harness.models.llama_cpp import LlamaCppModel

        return LlamaCppModel(
            model_path=config["model_path"],
            n_ctx=config.get("n_ctx", 4096),
            n_threads=config.get("n_threads"),
            n_gpu_layers=config.get("n_gpu_layers", 0),
        )

    if backend in {"openai", "openai_compat", "api", "vllm", "ollama"}:
        from rubric_harness.models.api import OpenAICompatModel

        return OpenAICompatModel(
            model_id=config["model_id"],
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key_env=config.get("api_key_env", "OPENAI_API_KEY"),
            timeout=config.get("timeout", 60.0),
        )

    raise ValueError(f"unknown model backend: {backend!r}")
