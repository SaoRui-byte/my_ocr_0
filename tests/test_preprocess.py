from PIL import Image

from core.preprocess import prepare_image, pdf_to_images


def test_prepare_image_downscales_large():
    img = Image.new("RGB", (3200, 2400))
    out = prepare_image(img)
    assert out.size == (2048, 1536)


def test_prepare_image_small_unchanged():
    img = Image.new("RGB", (800, 600))
    assert prepare_image(img).size == (800, 600)


def test_pdf_to_images_returns_rgb_pages(tmp_path):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    pdf.new_page(width=200, height=200)
    path = tmp_path / "blank.pdf"
    pdf.save(str(path))

    images = pdf_to_images(str(path))
    assert len(images) == 1
    assert images[0].mode == "RGB"
