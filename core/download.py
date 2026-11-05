"""自定义文件名的下载控件。

Streamlit 原生 ``st.download_button`` 的文件名是在脚本渲染时写进媒体 URL 的
``Content-Disposition`` 里的，而 ``st.text_input`` 的值要失焦/回车才会提交给后端。
用户输入新名字后直接点下载，用的还是上一次渲染的旧 URL，于是文件始终是默认名。

这里改为纯前端实现：文件名输入框与下载按钮同在一个组件内，点击下载时才读取
输入框的实时值，用 Blob 生成文件并指定 ``download`` 名称，一次点击即生效。
"""
import base64
import json
from html import escape as html_escape

import streamlit.components.v1 as components

_TEMPLATE = """
<div class="dl-wrap">
  <div class="dl-label">📝 文件名</div>
  <div class="dl-row">
    <input id="dl-name" type="text" spellcheck="false" autocomplete="off" value="__NAME_HTML__">
    <button id="dl-btn" type="button">⬇️ 下载</button>
  </div>
  <div class="dl-hint" id="dl-hint"></div>
</div>
<style>
  html, body { margin: 0; padding: 0; background: transparent; }
  body { font-family: "Source Sans Pro", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
  .dl-label { font-size: 13px; color: #64748b; margin: 0 0 6px; }
  .dl-row { display: flex; gap: 10px; align-items: center; }
  #dl-name {
    flex: 1 1 auto; min-width: 0; height: 38px; padding: 0 12px;
    border: 1px solid rgba(49, 51, 63, 0.25); border-radius: 8px;
    background: transparent; color: #1e293b; font-size: 14px; outline: none;
    box-sizing: border-box;
  }
  #dl-name:focus { border-color: #667eea; box-shadow: 0 0 0 1px #667eea; }
  #dl-btn {
    flex: 0 0 auto; height: 38px; padding: 0 18px; border: none; border-radius: 8px;
    background: #667eea; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
  }
  #dl-btn:hover { background: #5a6fd8; }
  .dl-hint { margin-top: 6px; font-size: 12px; color: #94a3b8; }
  html.dark .dl-label { color: #a3a8b8; }
  html.dark #dl-name { color: #fafafa; border-color: rgba(250, 250, 250, 0.3); }
  html.dark .dl-hint { color: #8b90a0; }
</style>
<script>
  const PAYLOAD = __PAYLOAD_JS__;
  const MIME = __MIME_JS__;
  const DEFAULT_NAME = __NAME_JS__;
  const EXT = __EXT_JS__;

  const nameInput = document.getElementById("dl-name");
  const hint = document.getElementById("dl-hint");

  function effectiveName() {
    let name = nameInput.value.trim() || DEFAULT_NAME;
    if (!/\\.(md|txt|xlsx|json)$/i.test(name)) {
      name += "." + EXT;
    }
    return name;
  }

  function updateHint() {
    hint.textContent = "将保存为：" + effectiveName();
  }

  document.getElementById("dl-btn").addEventListener("click", function () {
    const binary = atob(PAYLOAD);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const url = URL.createObjectURL(new Blob([bytes], { type: MIME }));
    const link = document.createElement("a");
    link.href = url;
    link.download = effectiveName();
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  nameInput.addEventListener("input", updateHint);
  updateHint();

  // 跟随 Streamlit 主题：读取父页面背景亮度，暗色主题下切换文字颜色
  try {
    const parentDoc = window.parent.document;
    const target = parentDoc.querySelector('[data-testid="stApp"]') || parentDoc.body;
    const bg = window.parent.getComputedStyle(target).backgroundColor;
    const rgb = bg.match(/\\d+/g);
    if (rgb && rgb.length >= 3) {
      const [r, g, b] = rgb.map(Number);
      if ((r + g + b) / 3 < 128) {
        document.documentElement.classList.add("dark");
      }
    }
  } catch (err) {}
</script>
"""

def custom_download(content: bytes, default_name: str, mime: str) -> None:
    """文件名输入 + 下载按钮。点击下载时使用输入框里的当前值。"""
    ext = default_name.rsplit(".", 1)[-1] if "." in default_name else "bin"
    html = (
        _TEMPLATE.replace("__NAME_HTML__", html_escape(default_name, quote=True))
        .replace("__PAYLOAD_JS__", json.dumps(base64.b64encode(content).decode("ascii")))
        .replace("__MIME_JS__", json.dumps(mime))
        .replace("__NAME_JS__", json.dumps(default_name))
        .replace("__EXT_JS__", json.dumps(ext))
    )
    components.html(html, height=96, scrolling=False)
