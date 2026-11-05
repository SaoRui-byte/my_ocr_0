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

# 侧边栏菜单定义：(key, emoji, 标题, 副标题, 接受 PDF?, 渲染函数)
MENU = [
    ("doc",    "📄", "文档转写", "图片 / PDF → Markdown（含公式 LaTeX）", True,  "doc_to_md"),
    ("table",  "📊", "表格提取", "图片 / PDF → 可编辑 Excel",             True,  "table_to_xlsx"),
    ("kie",    "🧾", "信息抽取", "发票 / 收据 → 结构化 Excel",           False, "kie"),
    ("vqa",    "🔍", "识字问答", "纯文字识别 或 对图片提问",             False, "vqa"),
]


@st.cache_resource
def load_service() -> OCRService:
    return OCRService().load()


def draw_sidebar(service: OCRService | None = None) -> str:
    """侧边栏：Logo + 导航菜单 + 关于信息。返回选中菜单的 key。"""
    with st.sidebar:
        # Logo
        st.markdown(
            """
            <div style="padding: 14px 18px; border-radius: 14px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; margin-bottom: 20px;">
                <div style="font-size: 20px; font-weight: 700;">📄 my_ocr_0</div>
                <div style="font-size: 12px; opacity: 0.85; margin-top: 6px;">
                    本地 OCR · 零上传 · 离线可用
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 导航菜单
        st.markdown("#### 🧭 功能")
        labels = [f"{item[1]} {item[2]}" for item in MENU]
        selected_label = st.radio(
            "选择功能",
            labels,
            index=0,
            label_visibility="collapsed",
            key="nav_menu",
        )
        selected_key = MENU[labels.index(selected_label)][0]

        st.divider()

        # 设备状态
        if service:
            device_label = {"cuda": "🔥 NVIDIA GPU", "xpu": "🔥 Intel XPU", "cpu": "🐢 CPU"}.get(
                service.device, service.device
            )
            st.markdown(f"<span style='color:#059669; font-size:13px;'>● {device_label}</span>", unsafe_allow_html=True)

        # 关于
        with st.expander("ℹ️ 关于"):
            st.caption(
                "基于开源模型 Xiaomi-OCR-0（0.8B）本地推理。"
                "图片不上传、完全离线可用。"
            )
            st.code("图片: PNG / JPG / WEBP / BMP\n文档: PDF")

    return selected_key


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def load_uploaded_images(uploaded_files) -> list[Image.Image]:
    images = []
    for f in uploaded_files:
        if f.name.lower().endswith(".pdf"):
            images.extend(pdf_to_images(f.getbuffer()))
        else:
            images.append(prepare_image(Image.open(f).convert("RGB")))
    return images


def upload_zone(key: str, accept_pdf: bool = True) -> list[Image.Image]:
    types = ALL_INPUT_TYPES if accept_pdf else SUPPORTED_IMAGE_TYPES
    hint = "图片或 PDF" if accept_pdf else "仅图片"
    files = st.file_uploader(f"📁 上传文件（{hint}）", type=types, key=f"{key}_up", accept_multiple_files=True)
    return load_uploaded_images(files) if files else []


def source_preview(md_text: str, key: str = "split") -> str:
    """左右分栏预览 Markdown，返回编辑后的文本。"""
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown("**📝 Markdown 源码**")
        edited = st.text_area("源码", value=md_text, height=480, key=f"{key}_src")
    with col_right:
        st.markdown("**👀 实时渲染**")
        st.markdown(edited)
    return edited


def page_header(title: str, subtitle: str, emoji: str) -> None:
    st.markdown(
        f"""
        <div style="padding: 16px 20px; border-radius: 12px;
                    background: #f8fafc; border-left: 4px solid #667eea;
                    margin-bottom: 24px;">
            <div style="font-size: 20px; font-weight: 600; color: #1e293b;">
                {emoji} {title}
            </div>
            <div style="font-size: 13px; color: #64748b; margin-top: 6px;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 辅助：带自定义文件名的下载
# ---------------------------------------------------------------------------

def custom_download(content: bytes, default_name: str, mime: str, key: str) -> None:
    """并排显示文件名输入框和下载按钮（标签外置以保证同行对齐）。"""
    st.markdown("📝 文件名")
    col_name, col_btn = st.columns([3, 2])
    with col_name:
        base = st.text_input("文件名", default_name, key=f"{key}_name", label_visibility="collapsed").strip() or default_name
    with col_btn:
        if not base.lower().endswith((".md", ".txt", ".xlsx", ".json")):
            base += "." + mime.split("/")[-1].replace("openxmlformats-officedocument.", "").replace("spreadsheetml.", "")
        st.download_button(
            "⬇️ 下载",
            content,
            file_name=base,
            mime=mime,
            type="primary",
            key=f"{key}_dl",
        )


# ---------------------------------------------------------------------------
# 各场景渲染
# ---------------------------------------------------------------------------

def render_doc_to_md(service: OCRService) -> None:
    page_header("文档转写", "上传图片或 PDF，输出保留结构与公式的 Markdown（公式为 LaTeX）。", "📄")
    images = upload_zone("doc", accept_pdf=True)
    if images and st.button("🚀 开始转写", type="primary"):
        progress = st.progress(0, text="转写中...")
        md_all = []
        for i, img in enumerate(images):
            with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
                md_all.append(service.parse(img))
            progress.progress((i + 1) / len(images))
        st.session_state["doc_result"] = "\n\n---\n\n".join(md_all)

    if "doc_result" in st.session_state:
        edited = source_preview(st.session_state["doc_result"], key="doc")
        custom_download(edited.encode("utf-8"), "document.md", "text/markdown", key="doc")


def render_table_to_xlsx(service: OCRService) -> None:
    page_header("表格提取", "把图片里的表格还原为可编辑 Excel，支持复杂表格、合并单元格。", "📊")
    images = upload_zone("table", accept_pdf=True)
    if images and st.button("🚀 开始识别", type="primary"):
        progress = st.progress(0, text="识别中...")
        md_all = []
        for i, img in enumerate(images):
            with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
                md_all.append(service.parse(img))
            progress.progress((i + 1) / len(images))
        st.session_state["table_result"] = "\n\n".join(md_all)

    if "table_result" in st.session_state:
        edited = source_preview(st.session_state["table_result"], key="table")
        xlsx = markdown_tables_to_excel(edited)
        if xlsx:
            custom_download(xlsx, "tables.xlsx", XLSX_MIME, key="table")
        else:
            st.warning("未检测到表格内容。")


def render_kie(service: OCRService) -> None:
    page_header("信息抽取", "上传发票或收据（可多张），自定义字段，自动汇总为 Excel。", "🧾")
    fields_input = st.text_input(
        "🔧 要抽取的字段（逗号分隔）",
        "商户名称,开票日期,发票号码,价税合计",
    )
    fields = [f.strip() for f in fields_input.replace("，", ",").split(",") if f.strip()]

    images = upload_zone("kie", accept_pdf=False)
    if images and st.button("🚀 抽取并汇总", type="primary"):
        progress = st.progress(0, text="抽取中...")
        records = []
        for i, img in enumerate(images):
            with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
                raw = service.kie(img, fields)
            try:
                records.append(extract_json(raw))
            except ValueError:
                st.warning(f"第 {i + 1} 张解析失败：{raw[:100]}")
            progress.progress((i + 1) / len(images))
        st.session_state["kie_result"] = records

    if st.session_state.get("kie_result"):
        records = st.session_state["kie_result"]
        st.markdown("#### 📋 抽取结果")
        st.json(records)
        custom_download(kie_to_excel(records), "invoices.xlsx", XLSX_MIME, key="kie")


def render_vqa(service: OCRService) -> None:
    page_header("识字问答", "纯文字识别，或直接对图片内容提问。", "🔍")
    sub = st.radio("模式", ["📝 纯文字识别", "❓ 对图片提问"], horizontal=True, key="vqa_sub")
    st.divider()

    if "纯文字" in sub:
        images = upload_zone("ocr", accept_pdf=False)
        if images and st.button("🚀 开始识别", type="primary"):
            progress = st.progress(0, text="识别中...")
            texts = []
            for i, img in enumerate(images):
                with st.spinner(f"第 {i + 1}/{len(images)} 张..."):
                    texts.append(service.parse(img))
                progress.progress((i + 1) / len(images))
            st.session_state["ocr_result"] = texts

        for i, text in enumerate(st.session_state.get("ocr_result", [])):
            st.markdown(f"#### 📌 第 {i + 1} 张")
            st.write(text)
            custom_download(text.encode("utf-8"), f"ocr_{i + 1}.md", "text/markdown", key=f"ocr_{i}")
    else:
        question = st.text_input("💬 你的问题", "这张图里金额是多少？")
        images = upload_zone("vqa", accept_pdf=False)
        if images and st.button("🚀 开始提问", type="primary"):
            answers = []
            for img in images:
                with st.spinner("思考中..."):
                    answers.append(service.vqa(img, question))
            st.session_state["vqa_result"] = answers

        for i, answer in enumerate(st.session_state.get("vqa_result", [])):
            st.markdown(f"#### 📌 第 {i + 1} 张回答")
            st.write(answer)
            custom_download(answer.encode("utf-8"), f"answer_{i + 1}.txt", "text/plain", key=f"vqa_{i}")


# key → 渲染函数的映射
RENDER = {
    "doc":   render_doc_to_md,
    "table": render_table_to_xlsx,
    "kie":   render_kie,
    "vqa":   render_vqa,
}


def main() -> None:
    try:
        service = load_service()
    except Exception as exc:
        # 模型加载失败也要能渲染侧边栏
        st.error(f"❌ 模型加载失败：{exc}")
        st.code(
            "from modelscope import snapshot_download\n"
            "snapshot_download('xiaomi-research/Xiaomi-OCR-0', local_dir='models/Xiaomi-OCR-0')"
        )
        draw_sidebar()
        return

    selected = draw_sidebar(service)
    RENDER[selected](service)

    # 页脚
    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #94a3b8; font-size: 13px; padding: 12px 0;">
            © 2026 <a href="https://github.com/SaoRui-Byte" target="_blank" style="color: #667eea; text-decoration: none;">SaoRui-Byte</a> · 
            Built with Xiaomi-OCR-0
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
