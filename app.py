"""my_ocr_0 — 基于 Xiaomi-OCR-0 的本地 OCR 工具（表格转 Excel / 文档转 Markdown / 发票整理 / 识字问答）。"""
import streamlit as st
from PIL import Image

from core.exporters import extract_json, kie_to_excel, markdown_tables_to_excel
from core.ocr_service import OCRService
from core.preprocess import pdf_to_images, prepare_image

st.set_page_config(page_title="my_ocr_0 — 本地 OCR", page_icon="📄", layout="wide")

SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "bmp"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_resource
def load_service() -> OCRService:
    return OCRService().load()


def draw_sidebar() -> None:
    """侧边栏：项目介绍 + 设备信息。"""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 16px; border-radius: 12px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; margin-bottom: 16px;">
                <div style="font-size: 18px; font-weight: 700;">📄 my_ocr_0</div>
                <div style="font-size: 12px; opacity: 0.85; margin-top: 4px;">
                    本地 OCR · 表格 · 发票 · 问答
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### 关于")
        st.caption(
            "基于开源模型 [Xiaomi-OCR-0](https://github.com/xiaomi-research/Xiaomi-OCR-0)（0.8B）本地推理。"
            "图片不上传、离线可用。"
        )
        st.markdown("### 支持格式")
        st.code("图片: PNG / JPG / WEBP / BMP\n文档: PDF")
        st.markdown("### 快捷键")
        st.caption("上传后点击「开始识别」即可，无页数限制。")


def load_uploaded_images(uploaded_files) -> list[Image.Image]:
    images = []
    for f in uploaded_files:
        if f.name.lower().endswith(".pdf"):
            images.extend(pdf_to_images(f.getbuffer()))
        else:
            images.append(prepare_image(Image.open(f).convert("RGB")))
    return images


def scene_images(key: str, uploader_types: list[str]) -> list[Image.Image]:
    """统一取图入口：文件上传（支持多图 / PDF）。"""
    files = st.file_uploader("📁 上传图片或 PDF", type=uploader_types, key=f"{key}_up", accept_multiple_files=True)
    if files:
        return load_uploaded_images(files)
    return []


def source_preview(md_text: str, key: str = "split") -> None:
    """左右分栏：左=Markdown 源码（可编辑），右=实时渲染预览。"""
    st.markdown("#### 💡 结果预览")
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown("**📝 Markdown 源码**")
        edited = st.text_area("源码", value=md_text, height=480, key=f"{key}_src")
    with col_right:
        st.markdown("**👀 实时渲染**")
        st.markdown(edited)


def section_header(title: str, subtitle: str, emoji: str = "✨") -> None:
    """统一的场景标题样式。"""
    st.markdown(
        f"""
        <div style="padding: 16px 20px; border-radius: 12px;
                    background: #f8fafc; border-left: 4px solid #667eea;
                    margin-bottom: 20px;">
            <div style="font-size: 18px; font-weight: 600; color: #1e293b;">
                {emoji} {title}
            </div>
            <div style="font-size: 13px; color: #64748b; margin-top: 6px;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    # ---- 顶部 Hero ----
    st.markdown(
        """
        <div style="text-align: center; padding: 24px 0 16px 0;">
            <h1 style="margin: 0 0 8px 0; font-size: 32px;">📄 my_ocr_0</h1>
            <p style="margin: 0; color: #64748b; font-size: 15px;">
                本地 OCR 识别工具 — 表格转 Excel · 文档转 Markdown · 发票整理 · 识字问答
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
        st.info("👉 请先下载模型：\n"
                "```python\nfrom modelscope import snapshot_download\n"
                "snapshot_download('xiaomi-research/Xiaomi-OCR-0', local_dir='models/Xiaomi-OCR-0')\n```")
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

    # ---- 四个场景 Tab ----
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 图片转 Excel", "📄 文档转 Markdown", "🧾 发票整理", "🔍 识字问答"]
    )

    # ---- Tab 1: 表格还原 ----
    with tab1:
        section_header(
            "图片转 Excel",
            "上传含表格的图片/截图，还原为可编辑 Excel。支持复杂表格、合并单元格。",
            emoji="📊",
        )
        images = scene_images("t1", SUPPORTED_IMAGE_TYPES)
        if images and st.button("🚀 开始识别", key="t1_go", type="primary"):
            progress = st.progress(0, text="识别中...")
            md_all = []
            for i, img in enumerate(images):
                with st.spinner(f"识别第 {i + 1}/{len(images)} 张..."):
                    md_all.append(service.parse(img))
                progress.progress((i + 1) / len(images))
            md_text = "\n\n".join(md_all)
            source_preview(md_text, key="t1")
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
                st.info("未在结果中检测到表格，可试试文档转 Markdown 场景。")

    # ---- Tab 2: 文档转 Markdown ----
    with tab2:
        section_header(
            "文档转 Markdown",
            "上传文档/扫描件/PDF，输出保留结构与公式的 Markdown（公式为 LaTeX）。单次最多 50 页。",
            emoji="📄",
        )
        images = scene_images("t2", SUPPORTED_IMAGE_TYPES + ["pdf"])
        if images and st.button("🚀 开始转换", key="t2_go", type="primary"):
            progress = st.progress(0, text="转换中...")
            md_all = []
            for i, img in enumerate(images):
                with st.spinner(f"转换第 {i + 1}/{len(images)} 张..."):
                    md_all.append(service.parse(img))
                progress.progress((i + 1) / len(images))
            md_text = "\n\n---\n\n".join(md_all)
            source_preview(md_text, key="t2")
            st.download_button(
                "⬇️ 下载 Markdown (.md)",
                md_text.encode("utf-8"),
                file_name="document.md",
                mime="text/markdown",
                type="primary",
            )

    # ---- Tab 3: 发票整理 ----
    with tab3:
        section_header(
            "发票整理",
            "上传发票/收据（可多张），抽取关键字段并汇总为 Excel。",
            emoji="🧾",
        )
        fields_text = st.text_input(
            "🔧 要抽取的字段（逗号分隔）",
            "商户名称,开票日期,发票号码,价税合计",
        )
        images = scene_images("t3", SUPPORTED_IMAGE_TYPES)
        if images and st.button("🚀 抽取并汇总", key="t3_go", type="primary"):
            progress = st.progress(0, text="抽取中...")
            fields = [f.strip() for f in fields_text.replace("，", ",").split(",") if f.strip()]
            records = []
            for i, img in enumerate(images):
                with st.spinner(f"抽取第 {i + 1}/{len(images)} 张..."):
                    raw = service.kie(img, fields)
                try:
                    records.append(extract_json(raw))
                except ValueError:
                    st.warning(f"部分结果解析失败，原始输出：\n{raw}")
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

    # ---- Tab 4: 识字问答 ----
    with tab4:
        section_header(
            "识字问答",
            "截图/手写/书法识别，或直接对文档内容提问。",
            emoji="🔍",
        )
        mode = st.radio(
            "模式",
            ["📝 提取全文（OCR）", "❓ 对文档提问（VQA）"],
            horizontal=True,
            key="t4_mode",
        )
        question = ""
        if "对文档" in mode:
            question = st.text_input("💬 你的问题", "这张图里金额是多少？")
        images = scene_images("t4", SUPPORTED_IMAGE_TYPES)
        if images and st.button("🚀 识别 / 提问", key="t4_go", type="primary"):
            for i, img in enumerate(images):
                with st.spinner(f"处理第 {i + 1}/{len(images)} 张..."):
                    answer = (
                        service.parse(img) if "提取全文" in mode else service.vqa(img, question)
                    )
                st.markdown(f"#### 📌 第 {i + 1} 张结果")
                st.write(answer)
                st.download_button(
                    "⬇️ 下载文本",
                    answer.encode("utf-8"),
                    file_name=f"answer_{i + 1}.txt",
                    mime="text/plain",
                    key=f"t4_dl{i}",
                )


if __name__ == "__main__":
    main()
