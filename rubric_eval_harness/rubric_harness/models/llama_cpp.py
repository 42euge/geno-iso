"""llama.cpp backend (lazy import).

Install with: pip install rubric-eval-harness[llamacpp]
"""

from __future__ import annotations

from rubric_harness.models.base import GenerationRequest, GenerationResult, ModelClient


class LlamaCppModel(ModelClient):
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_threads: int | None = None,
        n_gpu_layers: int = 0,
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise ImportError(
                "llama.cpp backend requires the 'llamacpp' extra: "
                "pip install rubric-eval-harness[llamacpp]"
            ) from e

        self.name = model_path
        self.llama = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        out = self.llama(
            request.prompt,
            max_tokens=request.max_new_tokens,
            temperature=request.temperature,
            seed=request.seed if request.seed is not None else -1,
            stop=request.stop or None,
        )
        choice = out["choices"][0]
        usage = out.get("usage", {})
        return GenerationResult(
            text=choice["text"],
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            finish_reason=choice.get("finish_reason", "stop"),
            raw={"backend": "llama_cpp", "model_path": self.name},
        )
