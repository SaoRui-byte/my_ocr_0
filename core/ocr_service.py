"""本地推理内核：transformers 加载 Xiaomi-OCR-0，prompt/解码参数与官方对齐。"""
from __future__ import annotations

import os
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

from core.prompts import kie_prompt, parse_prompt, vqa_prompt
from core.preprocess import prepare_image

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "Xiaomi-OCR-0"

# 官方 _chat 解码设置：temperature=0（贪心）、enable_thinking=False
CHAT_TEMPLATE_KWARGS = {"enable_thinking": False}
MAX_TOKENS_PARSE = 4096
MAX_TOKENS_VQA = 1024


def pick_device() -> str:
    """设备优先级：NVIDIA GPU (cuda) → Intel GPU (xpu) → CPU。"""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    return "cpu"


class OCRService:
    def __init__(self, model_dir: Path = MODEL_DIR, int8: bool = False, device: str | None = None):
        self.model_dir = Path(model_dir)
        self.int8 = int8 or os.environ.get("OCR_INT8") == "1"
        self.device = device or pick_device()
        self.model = None
        self.processor = None

    def load(self) -> "OCRService":
        if not (self.model_dir / "config.json").exists():
            raise FileNotFoundError(
                f"模型目录不存在或未下载: {self.model_dir}。"
                "请运行: python -c \"from modelscope import snapshot_download; "
                "snapshot_download('xiaomi-research/Xiaomi-OCR-0', local_dir='models/Xiaomi-OCR-0')\""
            )
        if self.device == "cpu":
            torch.set_num_threads(os.cpu_count() or 4)
        # CPU 用 float32（bf16 在 CPU 上反而更慢）；Arc/XMX 原生支持 bf16，约快一倍且省一半显存
        dtype = torch.float32 if self.device == "cpu" else torch.bfloat16
        self.processor = AutoProcessor.from_pretrained(str(self.model_dir), trust_remote_code=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            str(self.model_dir), dtype=dtype, trust_remote_code=True
        )
        if self.int8:
            if self.device != "cpu":
                raise ValueError("int8 动态量化仅支持 CPU 推理")
            self.model = torch.quantization.quantize_dynamic(self.model, {torch.nn.Linear}, dtype=torch.qint8)
        self.model.eval().to(self.device)
        return self

    def _generate(self, image: Image.Image, prompt: str, max_new_tokens: int) -> str:
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            chat_template_kwargs=CHAT_TEMPLATE_KWARGS,
        )
        inputs = self.processor(images=prepare_image(image), text=text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens,
                do_sample=False, repetition_penalty=1.0,
            )
        generated = output[:, inputs["input_ids"].shape[1]:]
        return self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def parse(self, image: Image.Image) -> str:
        from postprocess.document import finalize_document

        return finalize_document(self._generate(image, parse_prompt(), MAX_TOKENS_PARSE))

    def kie(self, image: Image.Image, fields: list[str] | None) -> str:
        return self._generate(image, kie_prompt(fields), MAX_TOKENS_PARSE)

    def vqa(self, image: Image.Image, question: str) -> str:
        return self._generate(image, vqa_prompt(question), MAX_TOKENS_VQA)
