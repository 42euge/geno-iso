"""Hugging Face transformers backend (lazy import).

Install with: pip install rubric-eval-harness[hf]
"""

from __future__ import annotations

from typing import Any

from rubric_harness.models.base import GenerationRequest, GenerationResult, ModelClient


class HFModel(ModelClient):
    def __init__(
        self,
        model_id: str,
        device: str | None = None,
        dtype: str = "auto",
        trust_remote_code: bool = False,
    ) -> None:
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:
            raise ImportError(
                "huggingface backend requires the 'hf' extra: "
                "pip install rubric-eval-harness[hf]"
            ) from e

        self.name = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=trust_remote_code
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=dtype,
            trust_remote_code=trust_remote_code,
        )
        if device:
            self.model = self.model.to(device)
        self.device = device or next(self.model.parameters()).device

    def generate(self, request: GenerationRequest) -> GenerationResult:
        import torch

        if request.seed is not None:
            torch.manual_seed(request.seed)

        inputs = self.tokenizer(request.prompt, return_tensors="pt").to(self.device)
        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": request.max_new_tokens,
            "do_sample": request.temperature > 0,
        }
        if request.temperature > 0:
            gen_kwargs["temperature"] = request.temperature

        with torch.no_grad():
            out = self.model.generate(**inputs, **gen_kwargs)
        completion_ids = out[0][inputs["input_ids"].shape[1] :]
        text = self.tokenizer.decode(completion_ids, skip_special_tokens=True)

        for stop in request.stop:
            idx = text.find(stop)
            if idx != -1:
                text = text[:idx]

        return GenerationResult(
            text=text,
            prompt_tokens=int(inputs["input_ids"].shape[1]),
            completion_tokens=int(completion_ids.shape[0]),
            raw={"backend": "hf", "model_id": self.name},
        )
