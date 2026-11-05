# Xiaomi-OCR-0 Streamlit Demo 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Streamlit 做出 Xiaomi-OCR-0 本地识别 demo，覆盖四大场景（表格转 Excel、文档转 Markdown、发票整理、识字问答），验证识别效果与场景吸引力。

**Architecture:** 单体 Streamlit 应用 + 统一推理内核（方案 A）。`core/` 封装 prompt 构建、预处理、导出、模型推理；`app.py` 只做 UI 与场景编排。模型经 ModelScope 下载到本地，transformers CPU 推理。

**Tech Stack:** Python 3.12、Streamlit、transformers + torch（CPU）、modelscope、pypdfium2、pandas + openpyxl、Pillow、pytest

**Spec:** `docs/superpowers/specs/2026-11-05-xiaomi-ocr-demo-design.md`

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `requirements.txt` | 依赖清单 |
| `core/prompts.py` | 三类任务 prompt 模板：parse / kie / vqa |
| `core/preprocess.py` | 图片缩放、PDF 转页图 |
| `core/exporters.py` | JSON 修复解析、Markdown 表格→Excel、KIE 记录→Excel |
| `core/ocr_service.py` | 模型加载与推理（parse/kie/vqa 三个入口） |
| `scripts/make_samples.py` | 生成 4 张合成示例图到 `samples/` |
| `scripts/smoke_model.py` | 模型冒烟脚本 |
| `app.py` | Streamlit UI：4 场景 Tab + 示例图库 + 假配额 + Pro 入口 |
| `tests/` | prompts / preprocess / exporters 单测（不依赖模型） |

---

### Task 1: 项目脚手架

**Files:**
- Create: `requirements.txt`, `core/__init__.py`, `tests/__init__.py`
- Create: `models/.gitkeep`, `samples/.gitkeep`

- [ ] **Step 1: 创建目录与依赖文件**

`requirements.txt`（torch 走 CPU 源安装见 Step 2）：

```text
streamlit>=1.38
transformers>=4.57
modelscope>=1.20
pypdfium2>=4.30
pandas>=2.2
openpyxl>=3.1
Pillow>=10.4
pytest>=8.0
```

`core/__init__.py` 与 `tests/__init__.py` 为空文件；创建 `models/`、`samples/` 目录并各放一个空 `.gitkeep`。

- [ ] **Step 2: 建虚拟环境并安装依赖（Windows PowerShell）**

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install -r requirements.txt
```

Expected: 全部安装成功。torch 为 CPU 版（约 200MB，而非 CUDA 版 2GB+）。

- [ ] **Step 3: 初始化 git 并提交**

```powershell
git init
git add requirements.txt core/__init__.py tests/__init__.py models/.gitkeep samples/.gitkeep docs/
git commit -m "chore: scaffold xiaomi-ocr demo project"
```

（执行时若用户未授权 git 提交，则跳过 commit，仅完成文件创建。）

---

### Task 2: core/prompts.py — 任务 prompt 模板

**Files:**
- Create: `core/prompts.py`
- Test: `tests/test_prompts.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_prompts.py
from core.prompts import parse_prompt, kie_prompt, vqa_prompt


def test_parse_prompt_mentions_markdown_and_latex():
    p = parse_prompt()
    assert "Markdown" in p
    assert "LaTeX" in p


def test_kie_prompt_lists_all_fields_and_json():
    p = kie_prompt(["金额", "日期"])
    assert "金额" in p and "日期" in p
    assert "JSON" in p


def test_kie_prompt_handles_empty_fields():
    p = kie_prompt([])
    assert "JSON" in p


def test_vqa_prompt_contains_question():
    assert "哪个季度" in vqa_prompt("哪个季度营收最高？")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_prompts.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.prompts'`

- [ ] **Step 3: 最小实现**

```python
# core/prompts.py
def parse_prompt() -> str:
    return (
        "请解析这份文档，按自然阅读顺序输出完整内容的 Markdown。"
        "表格用 Markdown 表格表示，数学公式用 LaTeX 表示。"
        "只输出结果，不要任何解释。"
    )


def kie_prompt(fields: list[str]) -> str:
    if fields:
        fields_text = "、".join(fields)
        return (
            f"请从图片中抽取以下字段：{fields_text}。"
            "以 JSON 对象输出，字段名作为键，未找到的字段值为 null。只输出 JSON。"
        )
    return "请抽取图片中的关键信息，以 JSON 对象输出。只输出 JSON。"


def vqa_prompt(question: str) -> str:
    return f"请根据图片内容回答问题：{question}"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_prompts.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```powershell
git add core/prompts.py tests/test_prompts.py
git commit -m "feat: add prompt templates for parse/kie/vqa"
```

---

### Task 3: core/preprocess.py — 预处理

**Files:**
- Create: `core/preprocess.py`
- Test: `tests/test_preprocess.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_preprocess.py
from PIL import Image
from core.preprocess import resize_image, pdf_to_images


def test_resize_large_image_downscales():
    img = Image.new("RGB", (3200, 2400))
    out = resize_image(img, max_side=1600)
    assert out.size == (1600, 1200)


def test_resize_small_image_unchanged():
    img = Image.new("RGB", (800, 600))
    assert resize_image(img).size == (800, 600)


def test_pdf_to_images_returns_rgb_pages(tmp_path):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    pdf.new_blank_page(width=200, height=200)
    path = tmp_path / "blank.pdf"
    pdf.save(str(path))

    images = pdf_to_images(str(path))
    assert len(images) == 1
    assert images[0].mode == "RGB"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_preprocess.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.preprocess'`

- [ ] **Step 3: 最小实现**

```python
# core/preprocess.py
from pathlib import Path

from PIL import Image

MAX_SIDE = 1600


def resize_image(img: Image.Image, max_side: int = MAX_SIDE) -> Image.Image:
    if max(img.size) <= max_side:
        return img
    scale = max_side / max(img.size)
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def pdf_to_images(path: str | Path, max_side: int = MAX_SIDE) -> list[Image.Image]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    images = []
    for i in range(len(pdf)):
        bitmap = pdf[i].render(scale=2.0)
        images.append(resize_image(bitmap.to_pil().convert("RGB"), max_side))
    return images
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_preprocess.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```powershell
git add core/preprocess.py tests/test_preprocess.py
git commit -m "feat: add image resize and pdf-to-images preprocessing"
```

---

### Task 4: core/exporters.py — 输出解析与导出

**Files:**
- Create: `core/exporters.py`
- Test: `tests/test_exporters.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_exporters.py
import io

import pandas as pd
import pytest

from core.exporters import extract_json, markdown_tables_to_excel, kie_to_excel


def test_extract_json_from_fenced_block():
    raw = '结果：\n```json\n{"a": 1}\n```\n'
    assert extract_json(raw) == {"a": 1}


def test_extract_json_from_noisy_text():
    raw = '答案是 {"金额": 12.5, "日期": "2026-11-05"} 希望有帮助'
    assert extract_json(raw) == {"金额": 12.5, "日期": "2026-11-05"}


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json("没有任何结构化数据")


def test_markdown_tables_to_excel():
    md = "| 姓名 | 分数 |\n|---|---|\n| 张三 | 90 |\n| 李四 | 85 |"
    data = markdown_tables_to_excel(md)
    df = pd.read_excel(io.BytesIO(data))
    assert list(df.columns) == ["姓名", "分数"]
    assert df.iloc[0]["姓名"] == "张三"


def test_kie_to_excel():
    data = kie_to_excel([{"商户": "小米", "金额": 99.0}])
    df = pd.read_excel(io.BytesIO(data))
    assert df.iloc[0]["商户"] == "小米"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_exporters.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.exporters'`

- [ ] **Step 3: 最小实现**

```python
# core/exporters.py
import io
import json
import re


def extract_json(raw: str):
    """从模型输出中解析 JSON；支持 ```json 代码块与含噪声文本。"""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\{\[]", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError(f"无法从模型输出中解析 JSON: {raw[:200]}")


def markdown_table_to_rows(table_md: str) -> list[list[str]]:
    rows = []
    for line in table_md.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue  # 表头分隔行
        rows.append(cells)
    return rows


def markdown_tables_to_excel(md_text: str) -> bytes:
    """抽取 Markdown 中所有表格写入一个多 sheet 的 xlsx，返回字节。"""
    import pandas as pd

    tables = re.findall(r"(?:^\|.*\|$\n?)+", md_text, re.M)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        index = 0
        for t in tables:
            rows = markdown_table_to_rows(t)
            if not rows:
                continue
            index += 1
            if len(rows) > 1:
                df = pd.DataFrame(rows[1:], columns=rows[0])
            else:
                df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=f"Table{index}", index=False)
    return buf.getvalue()


def kie_to_excel(records: list[dict]) -> bytes:
    """KIE 抽取记录（多张发票）汇总为 xlsx，返回字节。"""
    import pandas as pd

    buf = io.BytesIO()
    pd.DataFrame(records).to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_exporters.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add core/exporters.py tests/test_exporters.py
git commit -m "feat: add json repair and excel exporters"
```

---

### Task 5: core/ocr_service.py — 模型下载与推理内核

**Files:**
- Create: `core/ocr_service.py`
- Create: `scripts/smoke_model.py`

- [ ] **Step 1: 对齐官方 prompt 与加载方式**

用 WebFetch 抓取 `https://raw.githubusercontent.com/xiaomi-research/Xiaomi-OCR-0/main/SKILL.md` 和 `https://github.com/xiaomi-research/Xiaomi-OCR-0`（README/推理示例）。核对三点，如与本计划不一致**以官方为准更新代码**：
1. prompt 模板措辞（parse / KIE / VQA 的官方指令格式）
2. 模型加载类（`AutoModelForImageTextToText` 还是 `AutoModelForCausalLM`、是否 `trust_remote_code`）
3. 生成参数（max_new_tokens、采样方式）

- [ ] **Step 2: 下载模型到本地**

```powershell
.venv\Scripts\python -m pip install modelscope
.venv\Scripts\modelscope download --model xiaomi-research/Xiaomi-OCR-0 --local_dir models/Xiaomi-OCR-0
```

Expected: `models/Xiaomi-OCR-0/` 下出现 `config.json`、权重文件（*.safetensors）等。下载约 2-4GB，视网速需数分钟。

- [ ] **Step 3: 实现 OCRService**

```python
# core/ocr_service.py
from __future__ import annotations

import os
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

from core.prompts import parse_prompt, kie_prompt, vqa_prompt

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "Xiaomi-OCR-0"


class OCRService:
    def __init__(self, model_dir: Path = MODEL_DIR, max_new_tokens: int = 4096, int8: bool = False):
        self.model_dir = Path(model_dir)
        self.max_new_tokens = max_new_tokens
        self.int8 = int8 or os.environ.get("OCR_INT8") == "1"
        self.model = None
        self.processor = None

    def load(self) -> "OCRService":
        if not (self.model_dir / "config.json").exists():
            raise FileNotFoundError(
                f"模型目录不存在或未下载: {self.model_dir}。"
                "请运行: modelscope download --model xiaomi-research/Xiaomi-OCR-0 --local_dir models/Xiaomi-OCR-0"
            )
        torch.set_num_threads(os.cpu_count() or 4)
        self.processor = AutoProcessor.from_pretrained(str(self.model_dir), trust_remote_code=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            str(self.model_dir), torch_dtype=torch.float32, device_map="cpu", trust_remote_code=True
        )
        if self.int8:
            self.model = torch.quantization.quantize_dynamic(self.model, {torch.nn.Linear}, dtype=torch.qint8)
        self.model.eval()
        return self

    def _generate(self, image: Image.Image, prompt: str) -> str:
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(images=image.convert("RGB"), text=text, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens)
        generated = output[:, inputs["input_ids"].shape[1]:]
        return self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def parse(self, image: Image.Image) -> str:
        return self._generate(image, parse_prompt())

    def kie(self, image: Image.Image, fields: list[str]) -> str:
        return self._generate(image, kie_prompt(fields))

    def vqa(self, image: Image.Image, question: str) -> str:
        return self._generate(image, vqa_prompt(question))
```

（若 Step 1 显示官方加载方式不同，替换 `from_pretrained` 类名与模板调用。）

- [ ] **Step 4: 冒烟脚本验证单图识别**

```python
# scripts/smoke_model.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw

from core.ocr_service import OCRService

img = Image.new("RGB", (400, 120), "white")
ImageDraw.Draw(img).text((20, 40), "Hello OCR 2026 price=9.9", fill="black")

svc = OCRService().load()
print(svc.parse(img))
```

Run: `.venv\Scripts\python scripts\smoke_model.py`
Expected: 输出的 Markdown 中包含 `Hello OCR` 与 `9.9`（CPU 首次推理约几十秒）。

- [ ] **Step 5: Commit**

```powershell
git add core/ocr_service.py scripts/smoke_model.py
git commit -m "feat: add local OCRService with parse/kie/vqa inference"
```

---

### Task 6: scripts/make_samples.py — 合成示例图

**Files:**
- Create: `scripts/make_samples.py`
- Output: `samples/table.png`, `samples/formula.png`, `samples/receipt.png`, `samples/note.png`

- [ ] **Step 1: 实现生成脚本**

```python
# scripts/make_samples.py
"""生成 4 张合成示例图，覆盖四大场景（无需外部素材）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def make_table() -> None:
    img = Image.new("RGB", (640, 320), "white")
    d = ImageDraw.Draw(img)
    data = [["姓名", "部门", "金额"], ["张三", "研发部", "1200"], ["李四", "市场部", "860"], ["王五", "研发部", "2100"]]
    x0, y0, cw, rh = 60, 60, 170, 50
    for r, row in enumerate(data):
        for c, cell in enumerate(row):
            x, y = x0 + c * cw, y0 + r * rh
            d.rectangle([x, y, x + cw, y + rh], outline="black", width=2)
            d.text((x + 12, y + 15), cell, fill="black")
    img.save(SAMPLES / "table.png")


def make_formula() -> None:
    img = Image.new("RGB", (640, 300), "white")
    d = ImageDraw.Draw(img)
    lines = ["E = mc^2", "a^2 + b^2 = c^2", "x = (-b +- sqrt(b^2 - 4ac)) / 2a", "sum(i=1..n) i = n(n+1)/2"]
    for i, line in enumerate(lines):
        d.text((60, 50 + i * 60), line, fill="black")
    img.save(SAMPLES / "formula.png")


def make_receipt() -> None:
    img = Image.new("RGB", (420, 560), "white")
    d = ImageDraw.Draw(img)
    lines = [
        "电子发票（普通发票）",
        "商户名称：小米之家北京店",
        "开票日期：2026-11-05",
        "发票号码：260012345678",
        "商品：移动电源 x1",
        "金额：99.00 元",
        "税额：5.60 元",
        "价税合计：104.60 元",
    ]
    for i, line in enumerate(lines):
        d.text((40, 50 + i * 60), line, fill="black")
    img.save(SAMPLES / "receipt.png")


def make_note() -> None:
    img = Image.new("RGB", (640, 360), "white")
    d = ImageDraw.Draw(img)
    lines = [
        "项目周会纪要",
        "时间：2026年11月5日 14:00",
        "地点：3号会议室",
        "结论：下周三前完成初版评审。",
    ]
    for i, line in enumerate(lines):
        d.text((50, 50 + i * 70), line, fill="black")
    img.save(SAMPLES / "note.png")


if __name__ == "__main__":
    SAMPLES.mkdir(exist_ok=True)
    make_table()
    make_formula()
    make_receipt()
    make_note()
    print(f"生成完成: {sorted(p.name for p in SAMPLES.glob('*.png'))}")
```

注意：PIL 默认字体不支持中文会画出方块/报错。若本机无中文字体，在脚本顶部加载 Windows 自带字体：

```python
from PIL import ImageFont
FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
```

并把所有 `d.text(...)` 加 `font=FONT`。（执行此任务时按实际渲染结果调整，以示例图肉眼可读为准。）

- [ ] **Step 2: 运行脚本**

Run: `.venv\Scripts\python scripts\make_samples.py`
Expected: 输出 `生成完成: ['formula.png', 'note.png', 'receipt.png', 'table.png']`，4 张图肉眼可读。

- [ ] **Step 3: Commit**

```powershell
git add scripts/make_samples.py samples/
git commit -m "feat: add synthetic sample images generator"
```

---

### Task 7: app.py — Streamlit UI

**Files:**
- Create: `app.py`

- [ ] **Step 1: 实现应用**

```python
# app.py
import io

import streamlit as st
from PIL import Image

from core.exporters import extract_json, kie_to_excel, markdown_tables_to_excel
from core.ocr_service import OCRService
from core.preprocess import pdf_to_images, resize_image

st.set_page_config(page_title="Xiaomi OCR Demo", page_icon="📄", layout="wide")

FREE_PAGES_PER_DAY = 10
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "bmp"]


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


def load_images(uploaded_files) -> list[Image.Image]:
    images = []
    for f in uploaded_files:
        if f.name.lower().endswith(".pdf"):
            images.extend(pdf_to_images(f.read() if False else _save_tmp(f)))
        else:
            images.append(resize_image(Image.open(f).convert("RGB")))
    return images


def _save_tmp(uploaded) -> str:
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(uploaded.getbuffer())
    return path


def sample_picker(prefix: str, sample_name: str):
    from pathlib import Path
    p = Path("samples") / sample_name
    col1, col2 = st.columns([1, 2])
    with col1:
        if p.exists():
            st.image(str(p), caption="示例图", width=220)
    with col2:
        use = st.button(f"用示例图试试（{sample_name}）", key=f"{prefix}_sample")
    return p if (use and p.exists()) else None


def main() -> None:
    st.title("Xiaomi OCR Demo — 表格 · 公式 · 发票 · 问答")
    st.caption("基于开源模型 Xiaomi-OCR-0（0.8B）本地推理，图片不上传。")
    quota_bar()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 图片转 Excel", "📄 文档转 Markdown", "🧾 发票整理", "🔍 识字问答"])

    service = None
    try:
        service = load_service()
    except Exception as exc:
        st.error(f"模型加载失败：{exc}")

    # ---- Tab 1: 表格还原 ----
    with tab1:
        st.markdown("上传含表格的图片/截图，还原为可编辑 Excel。")
        sample = sample_picker("t1", "table.png")
        files = st.file_uploader("上传表格图片", type=SUPPORTED_IMAGE_TYPES, key="t1_up", accept_multiple_files=True)
        images = load_images(files) if files else []
        if sample:
            images = [resize_image(Image.open(sample).convert("RGB"))]
        if images and service and st.button("开始识别", key="t1_go"):
            if consume_pages(len(images)):
                md_all = []
                for img in images:
                    with st.spinner("识别中（CPU 约几十秒）..."):
                        md_all.append(service.parse(img))
                md_text = "\n\n".join(md_all)
                st.markdown("**识别结果（Markdown 表格）**")
                st.code(md_text, language="markdown")
                xlsx = markdown_tables_to_excel(md_text)
                st.download_button("下载 Excel (.xlsx)", xlsx, file_name="tables.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---- Tab 2: 文档转 Markdown ----
    with tab2:
        st.markdown("上传文档/扫描件/PDF，输出保留结构与公式的 Markdown。")
        sample = sample_picker("t2", "formula.png")
        files = st.file_uploader("上传图片或 PDF", type=SUPPORTED_IMAGE_TYPES + ["pdf"], key="t2_up", accept_multiple_files=True)
        images = load_images(files) if files else []
        if sample:
            images = [resize_image(Image.open(sample).convert("RGB"))]
        if images and service and st.button("开始转换", key="t2_go"):
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
        st.markdown("上传发票/收据（可多张），抽取字段并汇总。")
        sample = sample_picker("t3", "receipt.png")
        fields_text = st.text_input("要抽取的字段（逗号分隔）", "商户名称,开票日期,发票号码,价税合计")
        files = st.file_uploader("上传发票图片", type=SUPPORTED_IMAGE_TYPES, key="t3_up", accept_multiple_files=True)
        images = load_images(files) if files else []
        if sample:
            images = [resize_image(Image.open(sample).convert("RGB"))]
        if images and service and st.button("抽取并汇总", key="t3_go"):
            if consume_pages(len(images)):
                fields = [f.strip() for f in fields_text.split(",") if f.strip()]
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
                                       file_name="invoices.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---- Tab 4: 识字问答 ----
    with tab4:
        st.markdown("截图识字、手写识别，或直接对文档内容提问。")
        sample = sample_picker("t4", "note.png")
        question = st.text_input("问题（留空则提取全文）", "这张图里写了什么？提取全文。")
        files = st.file_uploader("上传图片", type=SUPPORTED_IMAGE_TYPES, key="t4_up", accept_multiple_files=True)
        images = load_images(files) if files else []
        if sample:
            images = [resize_image(Image.open(sample).convert("RGB"))]
        if images and service and st.button("识别/提问", key="t4_go"):
            if consume_pages(len(images)):
                for img in images:
                    with st.spinner("思考中..."):
                        answer = service.vqa(img, question or "提取图片中的全部文字。")
                    st.markdown("**回答**")
                    st.write(answer)
                    st.download_button("下载文本", answer.encode("utf-8"), file_name="answer.txt", mime="text/plain")


if __name__ == "__main__":
    main()
```

（执行时如官方 prompt 格式在 Task 5 有更新，UI 不受影响；`load_images` 中 PDF 路径按实测修正。）

- [ ] **Step 2: 启动应用人工验收**

Run: `.venv\Scripts\python -m streamlit run app.py`
Expected: 浏览器打开 `http://localhost:8501`，4 个 Tab 可见、示例图显示、额度栏显示 `剩余 10/10 页`。

- [ ] **Step 3: Commit**

```powershell
git add app.py
git commit -m "feat: add streamlit ui with four scene tabs and quota placeholder"
```

---

### Task 8: 集成验收

- [ ] **Step 1: 全量单元测试**

Run: `.venv\Scripts\python -m pytest tests -v`
Expected: 12 passed（prompts 4 + preprocess 3 + exporters 5）

- [ ] **Step 2: 四场景人工验收（对照 spec 第 4 节）**

1. Tab1 上传 `samples/table.png` → .xlsx 可打开且行列正确
2. Tab2 上传 `samples/formula.png` → Markdown 中公式为 LaTeX
3. Tab3 上传 `samples/receipt.png` → JSON 含商户/日期/金额字段
4. Tab4 用 `samples/note.png` 提问 → 回答与图内容一致
5. 上传乱文件/超大图 → 页面不崩溃
6. 额度递减与 Pro 入口正常展示

- [ ] **Step 3: Commit（如有修复）**

```powershell
git add -u
git commit -m "fix: integration fixes from acceptance run"
```

---

## Self-Review 记录

1. **Spec 覆盖**：四大场景（Task 7）、示例图库（Task 6）、本地推理（Task 5）、导出产物 xlsx/md/json（Task 4/7）、假配额+Pro 占位（Task 7）、错误处理（Task 4 JSON 修复 + Task 7 校验）、测试（Task 2/3/4）、验收标准（Task 8）——全覆盖。
2. **占位符扫描**：无 TBD/TODO；Task 5 Step 1 的"以官方为准"是明确的核对动作，非占位。
3. **类型一致性**：`parse/kie/vqa`（ocr_service）与 app.py 调用一致；`extract_json`/`markdown_tables_to_excel`/`kie_to_excel` 签名与测试一致；`resize_image`/`pdf_to_images` 一致。
