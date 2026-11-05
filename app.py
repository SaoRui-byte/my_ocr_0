"""my_ocr_0 — 基于 Xiaomi-OCR-0 的本地 OCR 工具。"""
import streamlit as st
from PIL import Image

from core.exporters import extract_json, kie_to_excel, markdown_tables_to_excel
from core.ocr_service import OCRService
from core.preprocess import pdf_to_images, prepare_image

st.set_page_config(page_title="my_ocr_0 — 本地 OCR", page_icon="📄", layout="wide")

SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "bmp"]
ALL_INPUT_TYPES = SUPPORTED_IMAGE_TYPES + ["pdf"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_resource
def load_service() -> OCRService:
    return OCRService().load()


def draw_sidebar() -> None:
    """侧边栏：项目介绍。"""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 16px; border-radius: 12px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; margin-bottom: 16px;">
                <div style="font-size: 18px; font-weight: 700;">📄 my_ocr_0</div>
                <div style="font-size: 12px; opacity: 0.85; margin-top: 4px;">
                    本地 OCR · 零上传 · 离线可用
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### 关于")
        st.caption(
            "基于开源模型 [Xiaomi-OCR-0](https://github.com/xiaomi-research/Xiaomi-OCR-0)（0.8B）本地推理。"
        )
        st.markdown("### 支持格式")
        st.code("图片: PNG / JPG / WEBP / BMP\n文档: PDF")


def load_uploaded_images(uploaded_files) -> list[Image.Image]:
    images = []
    for f in uploaded_files:
        if f.name.lower().endswith(".pdf"):
            images.extend(pdf_to_images(f.getbuffer()))
        else:
            images.append(prepare_image(Image.open(f).convert("RGB")))
    return images


def upload_zone(key: str, accept_pdf: bool = True) -> list[Image.Image]:
    """统一上传区，返回图片列表（PDF 会自动拆页）。"""
    types = ALL_INPUT_TYPES if accept_pdf else SUPPORTED_IMAGE_TYPES
    files = st.file_uploader(
        "📁 上传文件" + ("（图片或 PDF）" if accept_pdf else "（仅图片）"),
        type=types,
        key=f"{key}_up",
        accept_multiple_files=True,
    )
    return load_uploaded_images(files) if files else []


def source_preview(md_text: str, key: str = "split") -> None:
    """左右分栏预览 Markdown：左源码可编辑，右实时渲染。"""
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown("**📝 Markdown 源码**")
        edited = st.text_area("源码", value=md_text, height=480, key=f"{key}_src")
    with col_right:
        st.markdown("**👀 实时渲染**")
        st.markdown(edited)


def run_batch(images: list[Image.Image], service, mode: str = "parse") -> list[str]:
    """批量推理 + 进度条。mode: parse / kie / vqa。"""
    progress = st.progress(0, text="处理中...")
    results = []
    for i, img in enumerate(images):
        with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
            if mode == "parse":
                results.append(service.parse(img))
            elif mode == "kie":
                fields = st.session_state.get(f"kie_fields", None)
                results.append(service.kie(img, fields))
            elif mode == "vqa":
                question = st.session_state.get(f"vqa_question", "")
                results.append(service.vqa(img, question))
        progress.progress((i + 1) / len(images))
    return results


# ---------------------------------------------------------------------------
# 各场景渲染函数
# ---------------------------------------------------------------------------

def tab_doc_to_md(service: OCRService) -> None:
    """📄 文档转写：图片/PDF → Markdown（文本+表格+公式）。"""
    st.info("把截图、扫描件、PDF 转成可编辑的 Markdown，保留公式（LaTeX）和表格结构。")
    images = upload_zone("doc_to_md")
    if images and st.button("🚀 开始转写", key="doc_go", type="primary"):
        results = run_batch(images, service, mode="parse")
        md_text = "\n\n---\n\n".join(results)
        source_preview(md_text, key="doc")
        st.download_button(
            "⬇️ 下载 Markdown (.md)",
            md_text.encode("utf-8"),
            file_name="document.md",
            mime="text/markdown",
            type="primary",
        )


def tab_table_to_xlsx(service: OCRService) -> None:
    """📊 表格提取：图片/PDF → Excel。"""
    st.info("把图片里的表格还原为可编辑 Excel，支持复杂表格、合并单元格。")
    images = upload_zone("table")
    if images and st.button("🚀 开始识别", key="table_go", type="primary"):
        results = run_batch(images, service, mode="parse")
        md_text = "\n\n".join(results)
        source_preview(md_text, key="table")
        xlsx = markdown_tables_to_excel(md_text)
        if xlsx:
            st.download_button(
                "⬇️ 下载 Excel (.xlsx)",
                xlsx,
                file_name="tables.xlsx",
                mime=XLSX_MIME,
                type="primary",
            )
        else:
            st.warning("未检测到表格内容，可试试「文档转写」场景。")


def tab_kie(service: OCRService) -> None:
    """🧾 信息抽取：发票/单据 → 结构化 Excel。"""
    st.info("上传发票或收据（可多张），自定义要抽取的字段，自动汇总为 Excel。")
    st.text_input(
        "🔧 要抽取的字段（逗号分隔）",
        "商户名称,开票日期,发票号码,价税合计",
        key="kie_fields_input",
    )
    # 同步到 session 供 run_batch 使用
    st.session_state["kie_fields"] = [
        f.strip() for f in st.session_state.get("kie_fields_input", "").replace("，", ",").split(",") if f.strip()
    ]
    images = upload_zone("kie", accept_pdf=False)
    if images and st.button("🚀 抽取并汇总", key="kie_go", type="primary"):
        progress = st.progress(0, text="抽取中...")
        records = []
        fields = st.session_state["kie_fields"]
        for i, img in enumerate(images):
            with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
                raw = service.kie(img, fields)
            try:
                records.append(extract_json(raw))
            except ValueError:
                st.warning(f"第 {i + 1} 张解析失败，原始输出：\n{raw}")
            progress.progress((i + 1) / len(images))
        if records:
            st.markdown("#### 📋 抽取结果")
            st.json(records)
            st.download_button(
                "⬇️ 下载汇总 Excel (.xlsx)",
                kie_to_excel(records),
                file_name="invoices.xlsx",
                mime=XLSX_MIME,
                type="primary",
            )


def tab_vqa(service: OCRService) -> None:
    """🔍 识字 & 问答：提取全文 或 对图片提问。"""
    sub = st.radio(
        "模式",
        ["📝 纯文字识别", "❓ 对图片提问"],
        horizontal=True,
        key="vqa_sub",
    )
    st.divider()

    if "纯文字" in sub:
        st.info("从图片中提取全部文字内容。")
        images = upload_zone("ocr", accept_pdf=False)
        if images and st.button("🚀 开始识别", key="ocr_go", type="primary"):
            progress = st.progress(0, text="识别中...")
            for i, img in enumerate(images):
                with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
                    text = service.parse(img)
                progress.progress((i + 1) / len(images))
                st.markdown(f"#### 📌 第 {i + 1} 张")
                st.write(text)
                st.download_button(
                    "⬇️ 下载文本",
                    text.encode("utf-8"),
                    file_name=f"ocr_{i + 1}.md",
                    mime="text/markdown",
                    key=f"ocr_dl_{i}",
                )

    else:
        st.session_state["vqa_question"] = st.text_input(
            "💬 你的问题",
            "这张图里金额是多少？",
        )
        st.info("针对图片内容直接提问，模型会给出简洁回答。")
        images = upload_zone("vqa", accept_pdf=False)
        if images and st.button("🚀 开始提问", key="vqa_go", type="primary"):
            for i, img in enumerate(images):
                with st.spinner(f"思考中..."):
                    answer = service.vqa(img, st.session_state["vqa_question"])
                st.markdown(f"#### 📌 第 {i + 1} 张回答")
                st.write(answer)
                st.download_button(
                    "⬇️ 下载回答",
                    answer.encode("utf-8"),
                    file_name=f"answer_{i + 1}.txt",
                    mime="text/plain",
                    key=f"vqa_dl_{i}",
                )


def main() -> None:
    # ---- Hero ----
    st.markdown(
        """
        <div style="text-align: center; padding: 24px 0 16px 0;">
            <h1 style="margin: 0 0 8px 0; font-size: 32px;">📄 my_ocr_0</h1>
            <p style="margin: 0; color: #64748b; font-size: 15px;">
                基于 Xiaomi-OCR-0（0.8B）的本地 OCR 工具
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- 加载模型 ----
    try:
        service = load_service()
    except Exception as exc:
        st.error(f"❌ 模型加载失败：{exc}")
        st.code(
            "from modelscope import snapshot_download\n"
            "snapshot_download('xiaomi-research/Xiaomi-OCR-0', local_dir='models/Xiaomi-OCR-0')"
        )
        draw_sidebar()
        return

    device_label = {"cuda": "🔥 NVIDIA GPU", "xpu": "🔥 Intel XPU", "cpu": "🐢 CPU"}.get(
        service.device, service.device
    )
    st.markdown(
        f"<div style='text-align:center; margin-bottom: 16px;'>"
        f"<span style='background:#ecfdf5; color:#059669; padding:4px 12px; border-radius:999px; "
        f"font-size:13px;'>✅ 模型已就绪 · {device_label}</span></div>",
        unsafe_allow_html=True,
    )

    draw_sidebar()

    # ---- 按用户意图分 Tab ----
    tabs = st.tabs(
        [
            "📄 文档转写",
            "📊 表格提取",
            "🧾 信息抽取",
            "🔍 识字问答",
        ]
    )

    with tabs[0]:
        tab_doc_to_md(service)
    with tabs[1]:
        tab_table_to_xlsx(service)
    with tabs[2]:
        tab_kie(service)
    with tabs[3]:
        tab_vqa(service)


if __name__ == "__main__":
    main()
