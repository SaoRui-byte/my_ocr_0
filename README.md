# my_ocr_0

> 基于开源模型 **Xiaomi-OCR-0**（0.8B 视觉语言模型）的本地文档识别工具。
> 图片与 PDF 全程在你自己电脑上推理，输出的是可直接使用的 **Markdown / Excel / JSON**，不是一段纯文本。

支持复杂表格还原、数学公式转 LaTeX、发票字段抽取、图片问答；自动适配 NVIDIA GPU / Intel XPU / CPU，完全离线运行。

---

## 项目亮点

**1. 产物即成品，不是一段文字**
普通 OCR 给你一堆带坐标的文字行；这里每一步都落到可用文件：文档转 Markdown（含 LaTeX 公式）、表格转多 sheet Excel、发票字段汇总成 Excel、问答结果可单独保存。识别完就能直接交付，省掉「复制 → 粘贴 → 排版」的手工环节。

**2. 复杂表格与公式是一等公民**
模型按 OTSL 结构输出表格，项目内置官方后处理把 OTSL 转成 HTML 表格，再解析成单元格写入 Excel（含合并单元格占位、多表分 sheet）。数学公式统一规范为 Markdown 可渲染的 LaTeX。这是传统 OCR 引擎和多数云 API 做不到的部分。

**3. 图片不出本机，隐私零风险**
模型权重下载到本地，推理在本机完成，没有任何图片上传、没有云端额度、没有按量计费。合同、病历、证件、发票这类敏感材料可以放心跑。

**4. 一个模型，四条业务链**
文档转写 / 表格提取 / 信息抽取 / 识字问答共用同一个推理内核与预处理管线，只有 prompt 与解码预算不同。部署一次，四种场景都能用，而不是装四套引擎。

**5. 硬件自适应，没有 GPU 也能跑**
启动时自动探测 CUDA → Intel XPU → CPU；GPU/Arc 上使用 bfloat16，CPU 上使用 float32（CPU 上 bf16 反而更慢），并支持 `OCR_INT8=1` 开启 int8 动态量化进一步压缩内存与提速。

**6. 面向真实工作流，而不是单张图的 demo**
多图批量、PDF 逐页渲染（上限 50 页）、多表分 sheet、多张发票合并汇总；识别结果持久化在会话里，改文件名或下载都不会让结果消失。

**7. 下载体验做完整了**
文件名可自定义，且**输入后一次点击即生效**。这不是小事：Streamlit 原生 `download_button` 的文件名在脚本渲染时就被写进媒体 URL，而输入框的值要失焦/回车才提交，用户输入后直接点下载会拿到默认文件名。本项目改用前端组件内实时读取输入值 + Blob 生成文件，彻底绕开这个限制。

**8. 与官方推理实现严格对齐**
prompt 模板、解码参数（贪心解码、`repetition_penalty=1.0`、`enable_thinking=False`）、图像预处理（RGB + 最长边 2048 等比缩放）、文档后处理（OTSL 转换、数学分隔符规范化、长文本重复截断）均取自官方代码，效果不打折扣。

---

## 和其他 OCR 方案的区别

| 维度 | 传统 OCR（Tesseract / PaddleOCR 等） | 云 OCR API（百度 / 腾讯 / 阿里等） | 在线多模态大模型 | 本项目 |
|---|---|---|---|---|
| 输出形态 | 字符 / 行 + 坐标框 | 文本或固定字段 | 自然语言描述 | Markdown / 多 sheet Excel / JSON |
| 表格还原 | 需另配表格模型，合并单元格常丢失 | 部分支持，结构有限 | 多为文字描述 | OTSL → HTML → 可编辑 Excel |
| 数学公式 | 基本不支持 | 极少支持 | 能描述，难精确 | LaTeX，可直接渲染 |
| 版面与阅读顺序 | 依赖版面分析模块调参 | 服务端黑盒 | 弱 | 按阅读顺序组织，保留标题层级 |
| 图片隐私 | 本地，安全 | 必须上传 | 必须上传 | 本地，安全 |
| 费用 | 免费 | 按量计费 | 按 token 计费 | 一次部署，边际成本为 0 |
| 离线可用 | 是 | 否 | 否 | 是 |
| 手写 / 翻拍 / 书法 | 识别率明显下降 | 一般 | 较强 | 视觉语言模型，鲁棒性较好 |
| 图片问答 | 不支持 | 不支持 | 支持 | 支持（同一本地模型） |
| 部署形态 | 需自行搭管线 | 直接调 API | 直接调 API | 单机 Streamlit，一条命令启动 |

一句话总结：**传统 OCR 擅长「把图变成字」，云 API 擅长「不占本地资源地把图变成字」，本项目擅长「把图变成可直接使用的结构化文件」，并且不用把图片交出去。**

### 边界说明（不吹）

- 这是 0.8B 的小模型：超大规模印刷体批量识别，专用 OCR 引擎在吞吐上更划算。
- CPU 上单页约几十秒到两分钟；批量场景建议用 GPU。
- 复杂推理、跨页逻辑关系（如长表格跨页拼接）不如大模型，需要人工复核。
- 低分辨率、强畸变、印章遮挡的票据仍有误识风险。

---

## 四个场景

| 场景 | 输入 | 输出 | 适合谁 |
|---|---|---|---|
| 文档转写 | 图片 / PDF | 保留版面与公式的 Markdown（公式为 LaTeX） | 论文、教材、扫描件归档 |
| 表格提取 | 图片 / PDF | 可编辑 Excel（多表分 sheet，支持合并单元格） | 报表、对账单、实验数据 |
| 信息抽取 | 发票 / 收据图片（可多张） | 按自定义字段输出 JSON + 汇总 Excel | 报销、财务整理 |
| 识字问答 | 图片 | 纯文字识别 / 对图片提问 | 截图识字、手写、书法、快速提问 |

支持格式：图片 PNG / JPG / JPEG / WEBP / BMP；文档 PDF（单次最多 50 页）。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone git@github.com:SaoRui-byte/my_ocr_0.git
cd my_ocr_0
```

### 2. 安装依赖

按硬件环境选择一种 torch 安装方式：

```bash
# NVIDIA GPU（推荐）
pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/cu121

# Intel XPU（Windows + Arc 独显）
pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/xpu

# CPU 兜底
pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/cpu

# 其余依赖
pip install -r requirements.txt
```

### 3. 下载模型

```bash
python -c "from modelscope import snapshot_download; snapshot_download('xiaomi-research/Xiaomi-OCR-0', local_dir='models/Xiaomi-OCR-0')"
```

### 4. 启动

```bash
streamlit run app.py
```

打开 `http://localhost:8501` 即可使用。

### 5.（可选）模型冒烟测试

```bash
python scripts/smoke_model.py
```

会用一张合成小图跑一次解析，确认权重、tokenizer 与推理链路都正常。

---

## 设备与性能

自动探测并选择推理设备，无需手动配置：

| 设备 | 精度 | 说明 |
|---|---|---|
| NVIDIA GPU (CUDA) | bfloat16 | 速度最快，推荐 |
| Intel XPU（Arc / 核显） | bfloat16 | 原生 XMX 加速，显存占用更低 |
| CPU | float32 | 兜底方案，单页几十秒级 |

CPU 上可开启 int8 动态量化：

```powershell
$env:OCR_INT8 = "1"
streamlit run app.py
```

```bash
OCR_INT8=1 streamlit run app.py   # Linux / macOS
```

---

## 项目结构

```
my_ocr_0/
├── app.py                     # Streamlit 入口：侧边栏导航 + 四个场景
├── core/
│   ├── ocr_service.py         # 模型加载、设备选择、推理封装
│   ├── prompts.py             # parse / kie / vqa 的 prompt 模板（对齐官方）
│   ├── preprocess.py          # 图像缩放、PDF 逐页渲染
│   ├── exporters.py           # 表格/JSON → Excel、JSON 容错修复
│   └── download.py            # 自定义文件名的下载控件（纯前端 Blob）
├── third_party/Xiaomi-OCR-0/  # 官方后处理实现（OTSL → HTML 表格等）
├── models/Xiaomi-OCR-0/       # 模型权重（本地下载，不入库）
├── samples/                   # 本地示例图（不入库）
├── scripts/smoke_model.py     # 模型冒烟脚本
├── tests/                     # 单元测试（不依赖模型权重）
└── docs/                      # 设计文档与实施计划
```

---

## 实现要点

- **推理**：`transformers` 加载，`st.cache_resource` 保证进程内只加载一次权重；贪心解码（`do_sample=False`），关闭 thinking，`max_new_tokens` 按任务分档（解析 4096 / 问答 1024）。
- **预处理**：与官方 `_image_png` 一致——转 RGB、按最长边 2048 等比缩小；PDF 用 `pypdfium2` 以 2.0 倍缩放渲染成页图。
- **后处理**：OTSL 表格转 HTML、LaTeX 分隔符规范化（`\[...\]` / `\(...\)` → `$$...$$` / `$...$`）、超长输出尾部重复截断。
- **导出**：Markdown 中的 HTML 表格与管道表格都会被解析；每张表写入独立 sheet；KIE 记录直接转成汇总表。
- **状态**：识别结果存放在 `session_state`，编辑源码、改文件名、下载都不会触发结果丢失。

---

## 测试

```bash
pytest tests/ -v
```

覆盖 prompt 构造、Markdown/JSON → Excel 导出、JSON 修复与图像预处理，全部不依赖模型权重，可在 CI 或低配机器上跑。

---

## 注意事项

1. 首次启动要加载权重，CPU 上可能需要 30–60 秒，之后由缓存复用。
2. 图片不会上传到任何服务器，所有推理在本机完成。
3. CPU 推理速度有限，批量处理建议使用 GPU。
4. PDF 页数上限为 50，可在 `core/preprocess.py` 的 `pdf_to_images()` 中调整。
5. 模型目录缺失时页面会给出可复制的下载命令，不会白屏崩溃。

---

## License

项目代码以 Apache License 2.0 发布；模型权重遵循 Xiaomi-OCR-0 原始许可证。

## 致谢

- [Xiaomi Research](https://github.com/xiaomi-research) 开源的 Xiaomi-OCR-0 模型与后处理实现
- [Streamlit](https://streamlit.io/)、[Transformers](https://huggingface.co/docs/transformers)、[ModelScope](https://www.modelscope.cn/)、[pypdfium2](https://github.com/pypdfium2-team/pypdfium2) 等开源项目
