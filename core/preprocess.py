"""图像/ PDF 预处理。图像准备与官方 _image_png 一致：转 RGB 并按最长边 2048 等比缩小。"""
from pathlib import Path

from PIL import Image

from evaluation_pipeline.cropping import fit_image


def prepare_image(img: Image.Image) -> Image.Image:
    return fit_image(img.convert("RGB"))


def pdf_to_images(source, max_pages: int = 50) -> list[Image.Image]:
    """把 PDF（路径或字节）渲染为页图列表，最多 max_pages 页。"""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(source)
    images = []
    for i in range(min(len(pdf), max_pages)):
        bitmap = pdf[i].render(scale=2.0)
        images.append(prepare_image(bitmap.to_pil()))
    return images
