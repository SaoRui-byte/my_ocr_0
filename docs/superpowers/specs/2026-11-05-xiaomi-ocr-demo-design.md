# Xiaomi-OCR-0 识别工具 Demo 设计文档

日期：2026-11-05
状态：已确认（用户批准方案 A、C 端定位、Pro ¥9.9/月，要求尽快出 demo 验证识别效果）

## 1. 背景与目标

基于开源模型 [Xiaomi-OCR-0](https://www.modelscope.cn/models/xiaomi-research/Xiaomi-OCR-0)（0.8B，本地 CPU 可跑）做一个面向 C 端个人用户的 OCR 识别工具，用于变现。

模型三大能力：
1. **文档解析**：正文/复杂表格/数学公式 → Markdown、LaTeX，按阅读顺序还原
2. **关键信息抽取（KIE）**：发票、收据、卡证、表单 → 指定字段输出 JSON
3. **OCR 视觉问答（VQA）**：对文档/图表做检索、计算、语义推理

**本阶段目标**：用 Streamlit 快速做出 demo，验证 (a) 识别效果（尤其表格/公式/翻拍鲁棒性）、(b) 哪个场景最吸引人。变现只做 UI 占位，不接支付。

## 2. 产品设计

### 2.1 定位

「免费好用的 AI 文档识别工具——表格、公式、发票都能变成可编辑的干净数据」。

差异化武器：便宜（免费额度大方）+ 表格/公式还原质量 + 隐私（本地识别，图片不上传）+ 场景闭环（识别 → 可用产物下载）。

### 2.2 四大场景（首页 Tab 顺序即获客漏斗）

| 顺序 | 场景 | 角色 | 亮点展示 |
|---|---|---|---|
| 1 | 图片转 Excel / 表格还原 | 获客钩子 | 复杂合并单元格表格还原成 .xlsx |
| 2 | PDF/文档转 Markdown | 深度需求、留存 | 阅读顺序、公式转 LaTeX、版面结构保留 |
| 3 | 发票/收据整理 | 付费意愿最强 | 指定字段 → JSON + 汇总 Excel（KIE） |
| 4 | 识字问答工具箱 | 引流 + 留存 | 截图识字、手写、对文档提问（VQA） |

### 2.3 转化设计

- 每个场景内置示例图库（含高难度样例：翻拍屏幕、倾斜纸张、复杂表格、数学公式），免上传一键体验
- 结果页直接给出可用产物下载（.xlsx / .md / .json），不是纯文本
- 明示「本地识别，图片不上传」隐私卖点

### 2.4 变现分层（demo 仅 UI 占位）

- **免费**：每日 10 页、单文件 ≤3 页、导出带水印
- **Pro 订阅 ¥9.9/月**：批量处理、无限页、无水印、全部格式导出、历史记录
- **按次包 ¥5/100 页**：低频用户兜底
- Demo 中做假配额提示（session_state 计数）和 Pro 升级入口

## 3. 技术设计

### 3.1 架构（方案 A：单体 Streamlit + 统一推理内核）

```
xiaomi_ocr_0/
├── app.py                  # Streamlit UI：4 场景 Tab + 示例图库 + 配额占位
├── core/
│   ├── ocr_service.py      # 模型加载（st.cache_resource）+ 推理封装
│   ├── prompts.py          # 三类任务 prompt 模板：parse / kie / vqa
│   ├── preprocess.py       # 图片缩放（长边≤1600）、PDF 转页图（pypdfium2）
│   └── exporters.py        # Markdown / JSON / Excel 导出 + JSON 修复
├── models/Xiaomi-OCR-0/    # ModelScope 下载的权重（不入库）
├── samples/                # 每场景 2-3 张示例图
└── tests/                  # prompts / exporters / JSON 修复单测（不依赖模型）
```

依赖：streamlit、transformers、torch（CPU 版）、modelscope、pypdfium2、pandas、openpyxl、Pillow。

### 3.2 数据流

上传或选示例 → 预处理（缩放 / PDF 转页图）→ 场景 → prompt 模板（parse / kie / vqa）→ 本地 CPU 推理 → 输出解析（JSON 修复兜底）→ 结果展示 + 下载。

### 3.3 推理

- 模经 ModelScope 下载到 `models/Xiaomi-OCR-0/`，transformers 加载（CPU），`st.cache_resource` 保证只加载一次
- 提速手段：图片长边压缩至 ≤1600、`torch.set_num_threads` 按 CPU 核数设置、int8 动态量化可选开关、限 max_new_tokens
- 预期速度：单页约几十秒到 2 分钟（CPU-only，无 NVIDIA GPU），demo 可接受

### 3.4 错误处理

- 文件类型/大小校验（图片：jpg/png/webp/bmp；PDF 页数限制）
- 模型加载失败 → 显示可操作的错误提示，不崩页面
- KIE 输出 JSON 解析失败 → 自动修复（提取 ```json 块或首个完整 `{...}`），修复失败展示原始文本
- 推理异常 → 友好错误信息 + 重试提示

### 3.5 测试

- 单元测试（不依赖模型）：prompt 模板构建、Markdown/JSON/Excel 导出、JSON 修复
- 人工验收清单：4 场景各跑示例图 + 实拍图，验收标准见第 4 节

## 4. 验收标准

1. 四个场景 Tab 全部可跑通，示例图一键出结果
2. 表格图片 → 可打开的 .xlsx；含公式文档 → LaTeX；发票 → 字段 JSON + 汇总表
3. 翻拍/倾斜/光照差的样例识别质量可接受
4. 单页 CPU 推理在几十秒级（可接受上限 2 分钟）
5. 错误输入不导致页面崩溃
6. 假配额提示与 Pro 升级入口正常展示
