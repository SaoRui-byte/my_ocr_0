"""输出解析与导出：JSON 修复、HTML/Markdown 表格 → Excel、KIE 记录 → Excel。"""
import io
import json
import re
from html.parser import HTMLParser


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


class _TableGridParser(HTMLParser):
    """把 <table> 解析为二维网格；rowspan/colspan 覆盖的位置补空串。"""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._rows: list[list[str]] | None = None
        self._occupied: set[tuple[int, int]] = set()
        self._cell: tuple[int, int] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._rows = []
            self._occupied = set()
        elif tag == "tr" and self._rows is not None:
            self._rows.append([])
        elif tag in ("td", "th") and self._rows:
            attrs = dict(attrs)
            r = len(self._rows) - 1
            row = self._rows[r]
            c = len(row)
            while (r, c) in self._occupied:
                row.append("")
                c += 1
            rowspan = max(1, int(attrs.get("rowspan") or 1))
            colspan = max(1, int(attrs.get("colspan") or 1))
            for rr in range(r, r + rowspan):
                for cc in range(c, c + colspan):
                    if (rr, cc) != (r, c):
                        self._occupied.add((rr, cc))
            row.append("")
            self._cell = (r, c)

    def handle_data(self, data):
        if self._cell is not None:
            r, c = self._cell
            self._rows[r][c] += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            r, c = self._cell
            self._rows[r][c] = self._rows[r][c].strip()
            self._cell = None
        elif tag == "tr" and self._rows is not None:
            row = self._rows[-1]
            while (len(self._rows) - 1, len(row)) in self._occupied:
                row.append("")
        elif tag == "table" and self._rows is not None:
            width = max((len(row) for row in self._rows), default=0)
            for row in self._rows:
                row.extend([""] * (width - len(row)))
            self.tables.append(self._rows)
            self._rows = None


def html_tables_to_grids(html: str) -> list[list[list[str]]]:
    parser = _TableGridParser()
    parser.feed(html)
    return parser.tables


def markdown_table_to_rows(table_md: str) -> list[list[str]]:
    rows = []
    for line in table_md.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue  # 表头分隔行
        rows.append(cells)
    return rows


def markdown_tables_to_excel(md_text: str) -> bytes | None:
    """抽取 Markdown 中的 HTML 表格（官方 OTSL 转换产物）与管道表格，写入多 sheet xlsx。"""
    import pandas as pd

    grids: list[list[list[str]]] = []
    for html in re.findall(r"<table>[\s\S]*?</table>", md_text):
        grids.extend(html_tables_to_grids(html))
    for table in re.findall(r"(?:^\|.*\|$\n?)+", md_text, re.M):
        rows = markdown_table_to_rows(table)
        if rows:
            grids.append(rows)
    if not grids:
        return None
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for i, rows in enumerate(grids, 1):
            if len(rows) > 1:
                df = pd.DataFrame(rows[1:], columns=rows[0])
            else:
                df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=f"Table{i}", index=False)
    return buf.getvalue()


def kie_to_excel(records: list[dict]) -> bytes:
    """KIE 抽取记录（多张发票）汇总为 xlsx。"""
    import pandas as pd

    buf = io.BytesIO()
    pd.DataFrame(records).to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()
