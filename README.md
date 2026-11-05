# my_ocr_0 📄

> 基于开源模型 **Xiaomi-OCR-0**（0.8B）的本地 OCR 工具，支持表格识别、文档解析、发票抽取和视觉问答。图片不上传，完全离线可用。

## ✨ 功能特性

| 场景 | 说明 |
|------|------|
| 📊 图片转 Excel | 上传含表格的图片/截图，还原为可编辑 Excel（支持合并单元格） |
| 📄 文档转 Markdown | 上传文档/扫描件/PDF，输出保留结构与公式的 Markdown（公式为 LaTeX） |
| 🧾 发票整理 | 上传发票/收据（可多张），抽取关键字段并汇总为 Excel |
| 🔍 识字问答 | 截图/手写/书法识别，或直接对文档内容提问 |

## 🖼️ 支持格式

- **图片**: PNG / JPG / JPEG / WEBP / BMP
- **文档**: PDF（单次最多 50 页）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd my_ocr_0
```

### 2. 安装依赖

按你的硬件环境选择 `torch` 安装方式（三选一）：

```bash
# --- NVIDIA GPU (推荐) ---
pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/cu121

# --- Intel XPU (Windows 本地 Arc) ---
pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/xpu

# --- CPU 兜底 ---
pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/cpu

# 安装其他依赖
pip install -r requirements.txt
```

### 3. 下载模型

```bash
python -c "from modelscope import snapshot_download; snapshot_download('xiaomi-research/Xiaomi-OCR-0', local_dir='models/Xiaomi-OCR-0')"
```

> 模型文件约 1.5GB，首次运行时会自动加载到内存。

### 4. 启动应用

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501` 即可使用。

## 🏗️ 项目结构

```
my_ocr_0/
├── app.py                  # Streamlit 前端入口
├── requirements.txt        # Python 依赖
├── models/
│   └── Xiaomi-OCR-0/      # 模型文件（需自行下载）
├── samples/               # 示例图片（可选）
├── core/
│   ├── __init__.py
│   ├── ocr_service.py     # 模型加载与推理内核
│   ├── preprocess.py      # 图像 / PDF 预处理
│   ├── exporters.py       # JSON 修复、表格 → Excel 导出
│   └── prompts.py         # 各任务 Prompt 模板
├── third_party/
│   └── Xiaomi-OCR-0/      # 官方后处理代码
├── scripts/               # 辅助脚本
└── tests/                 # 单元测试
```

## 💻 设备支持

自动检测并选择最佳推理设备：

| 设备 | 说明 |
|------|------|
| 🔥 NVIDIA GPU (CUDA) | 推荐，速度最快，使用 bfloat16 |
| 🔥 Intel XPU | Windows Arc / 独显原生支持 bfloat16 |
| 🐢 CPU | 兜底方案，使用 float32，约几十秒/页 |

CPU 上可通过环境变量启用 int8 量化加速：

```bash
set OCR_INT8=1
streamlit run app.py
```

## 🧪 运行测试

```bash
pytest tests/ -v
```

## 📝 技术栈

- **[Xiaomi-OCR-0](https://github.com/xiaomi-research/Xiaomi-OCR-0)** — 0.8B 视觉语言模型
- **[Streamlit](https://streamlit.io/)** — Web UI 框架
- **[Transformers](https://huggingface.co/docs/transformers)** — 模型加载与推理
- **[ModelScope](https://www.modelscope.cn/)** — 模型下载
- **pypdfium2** — PDF 渲染
- **pandas + openpyxl** — Excel 导出

## ⚠️ 注意事项

1. **首次加载模型较慢**（CPU 约 30-60 秒），后续推理会被 Streamlit `cache_resource` 缓存。
2. **图片不会上传到任何服务器**，所有推理在本地完成。
3. **CPU 推理速度有限**，处理大量图片建议使用 GPU。
4. **PDF 页数上限 50 页**，可在 `core/preprocess.py` 的 `pdf_to_images()` 中调整。

## 📄 License

本项目代码基于 [Apache License 2.0](LICENSE) 开源。模型权重遵循其原始许可证。

## 🙏 致谢

- [Xiaomi Research](https://github.com/xiaomi-research) 开源的 **Xiaomi-OCR-0** 模型
