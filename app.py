"""Xiaomi OCR Demo — 本地识别 Streamlit 应用（表格转 Excel / 文档转 Markdown / 发票整理 / 识字问答）。"""
from pathlib import Path

import streamlit as st
from PIL import Image

from core.exporters import extract_json, kie_to_excel, markdown_tables_to_excel
from core.ocr_service import OCRService
from core.preprocess import pdf_to_images, prepare_image

st.set_page_config(page_title="Xiaomi OCR Demo", page_icon="📄", layout="wide")

FREE_PAGES_PER_DAY = 10
SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "bmp"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

TAB1_SAMPLES = ["showcase_dense.png", "sample_document.png"]
TAB2_SAMPLES = ["sample_document.png", "showcase_formula.png", "showcase_dense.png"]
TAB3_SAMPLES = ["showcase_invoice.png", "sample_kie.png"]
TAB4_SAMPLES = ["sample_vqa.png", "showcase_whiteboard.png", "showcase_calligraphy.png"]


@st.cache_resource
def load_service() -> OCRService:
    return OCRService().load()


def quota_bar() -> None:
    used = st.session_state.get("used_pages", 0)
    left = max(FREE_PAGES_PER_DAY - used, 0)
    st.sidebar.markdown(f"### 今日额度：剩余 {left}/{FREE_PAGES_PER_DAY} 页")
    st.sidebar.caption("本地识别，图片不上传")
    if st.sidebar.button("升级 Pro（¥9.9/月）：无限页数、批量、无水印"):
        st.sidebar.info("Demo 占位：支付未接入，尽情体验全部功能。")


def consume_pages(n: int) -> bool:
    used = st.session_state.get("used_pages", 0)
    if used + n > FREE_PAGES_PER_DAY:
        st.warning("今日免费额度已用完（Demo 假配额，刷新页面重置）。升级 Pro 解除限制。")
        return False
    st.session_state["used_pages"] = used + n
    return True


def load_uploaded_images(uploaded_files) -> list[Image.Image]:
    images = []
    for f in uploaded_files:
        if f.name.lower().endswith(".pdf"):
            images.extend(pdf_to_images(f.getbuffer()))
        else:
            images.append(prepare_image(Image.open(f).convert("RGB")))
    return images


def scene_images(key: str, sample_names: list[str], uploader_types: list[str]) -> list[Image.Image]:
    """统一取图入口：示例图下拉 或 文件上传，二选一。"""
    choice = st.selectbox("示例图（免上传直接体验）", ["不使用"] + sample_names, key=f"{key}_sample")
    files = st.file_uploader("上传图片", type=uploader_types, key=f"{key}_up", accept_multiple_files=True)
    if files:
        return load_uploaded_images(files)
    if choice != "不使用" and (SAMPLES_DIR / choice).exists():
        return [prepare_image(Image.open(SAMPLES_DIR / choice).convert("RGB"))]
    return []


def main() -> None:
    st.title("Xiaomi OCR Demo — 表格 · 公式 · 发票 · 问答")
    st.caption("基于开源模型 Xiaomi-OCR-0（0.8B）本地推理，图片不上传。")

    try:
        service = load_service()
    except Exception as exc:
        st.error(f"模型加载失败：{exc}")
        quota_bar()
        return

    device_label = {"cuda": "NVIDIA GPU", "xpu": "Intel XPU", "cpu": "CPU"}.get(service.device, service.device)
    st.caption(f"推理设备：{device_label}")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 图片转 Excel", "📄 文档转 Markdown", "🧾 发票整理", "🔍 识字问答"])

    # ---- Tab 1: 表格还原 ----
    with tab1:
        st.markdown("上传含表格的图片/截图，还原为可编辑 Excel（复杂表格、合并单元格）。")
        images = scene_images("t1", TAB1_SAMPLES, SUPPORTED_IMAGE_TYPES)
        if images and st.button("开始识别", key="t1_go"):
            if consume_pages(len(images)):
                md_all = []
                for img in images:
                    with st.spinner("识别中（CPU 约几十秒）..."):
                        md_all.append(service.parse(img))
                md_text = "\n\n".join(md_all)
                st.markdown("**识别结果（Markdown / HTML 表格）**")
                st.code(md_text, language="markdown")
                xlsx = markdown_tables_to_excel(md_text)
                if xlsx:
                    st.download_button("下载 Excel (.xlsx)", xlsx, file_name="tables.xlsx", mime=XLSX_MIME)
                else:
                    st.info("未在结果中检测到表格，可试试文档转 Markdown 场景。")

    # ---- Tab 2: 文档转 Markdown ----
    with tab2:
        st.markdown("上传文档/扫描件/PDF，输出保留结构与公式的 Markdown（公式为 LaTeX）。单次最多处理 50 页。")
        images = scene_images("t2", TAB2_SAMPLES, SUPPORTED_IMAGE_TYPES + ["pdf"])
        if images and st.button("开始转换", key="t2_go"):
            if consume_pages(len(images)):
                md_all = []
                for img in images:
                    with st.spinner("转换中（CPU 约几十秒）..."):
                        md_all.append(service.parse(img))
                md_text = "\n\n---\n\n".join(md_all)
                st.markdown(md_text)
                st.download_button("下载 Markdown (.md)", md_text.encode("utf-8"),
                                   file_name="document.md", mime="text/markdown")

    # ---- Tab 3: 发票整理 ----
    with tab3:
        st.markdown("上传发票/收据（可多张），抽取字段并汇总为 Excel。")
        fields_text = st.text_input("要抽取的字段（逗号分隔）", "商户名称,开票日期,发票号码,价税合计")
        images = scene_images("t3", TAB3_SAMPLES, SUPPORTED_IMAGE_TYPES)
        if images and st.button("抽取并汇总", key="t3_go"):
            if consume_pages(len(images)):
                fields = [f.strip() for f in fields_text.replace("，", ",").split(",") if f.strip()]
                records = []
                for img in images:
                    with st.spinner("抽取中..."):
                        raw = service.kie(img, fields)
                    try:
                        records.append(extract_json(raw))
                    except ValueError:
                        st.warning(f"部分结果解析失败，原始输出：\n{raw}")
                if records:
                    st.json(records)
                    st.download_button("下载汇总 Excel (.xlsx)", kie_to_excel(records),
                                       file_name="invoices.xlsx", mime=XLSX_MIME)

    # ---- Tab 4: 识字问答 ----
    with tab4:
        st.markdown("截图/手写/书法识别，或直接对文档内容提问。")
        mode = st.radio("模式", ["提取全文（OCR）", "对文档提问（VQA）"], horizontal=True, key="t4_mode")
        question = ""
        if mode.startswith("对文档"):
            question = st.text_input("问题", "这张图里金额是多少？")
        images = scene_images("t4", TAB4_SAMPLES, SUPPORTED_IMAGE_TYPES)
        if images and st.button("识别 / 提问", key="t4_go"):
            if consume_pages(len(images)):
                for img in images:
                    with st.spinner("思考中..."):
                        answer = service.parse(img) if mode.startswith("提取全文") else service.vqa(img, question)
                    st.markdown("**结果**")
                    st.write(answer)
                    st.download_button("下载文本", answer.encode("utf-8"), file_name="answer.txt",
                                       mime="text/plain", key=f"t4_dl{id(img)}")

    quota_bar()  # 在场景处理之后渲染额度，点击识别后立即显示最新余量


if __name__ == "__main__":
    main()
