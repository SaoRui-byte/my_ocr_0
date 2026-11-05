"""模型冒烟：加载本地权重并对合成小图做一次解析。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw

from core.ocr_service import OCRService

img = Image.new("RGB", (400, 120), "white")
ImageDraw.Draw(img).text((20, 40), "Hello OCR 2026 price=9.9", fill="black")

svc = OCRService().load()
print(svc.parse(img))
