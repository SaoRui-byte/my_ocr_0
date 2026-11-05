import io

import pandas as pd
import pytest

from core.exporters import (
    extract_json,
    html_tables_to_grids,
    markdown_tables_to_excel,
    kie_to_excel,
)


def test_extract_json_from_fenced_block():
    raw = '结果：\n```json\n{"a": 1}\n```\n'
    assert extract_json(raw) == {"a": 1}


def test_extract_json_from_noisy_text():
    raw = '答案是 {"金额": 12.5, "日期": "2026-11-05"} 希望有帮助'
    assert extract_json(raw) == {"金额": 12.5, "日期": "2026-11-05"}


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json("没有任何结构化数据")


def test_markdown_pipe_table_to_excel():
    md = "| 姓名 | 分数 |\n|---|---|\n| 张三 | 90 |\n| 李四 | 85 |"
    data = markdown_tables_to_excel(md)
    df = pd.read_excel(io.BytesIO(data))
    assert list(df.columns) == ["姓名", "分数"]
    assert df.iloc[0]["姓名"] == "张三"


def test_html_table_with_spans_to_grids():
    html = '<table><tr><td rowspan="2">张三</td><td>90</td></tr><tr><td>85</td></tr></table>'
    grids = html_tables_to_grids(html)
    assert grids == [[["张三", "90"], ["", "85"]]]


def test_html_table_to_excel():
    md = '<table><tr><td>姓名</td><td>分数</td></tr><tr><td>张三</td><td>90</td></tr></table>'
    data = markdown_tables_to_excel(md)
    df = pd.read_excel(io.BytesIO(data))
    assert df.iloc[0]["姓名"] == "张三"
    assert df.iloc[0]["分数"] == 90


def test_markdown_tables_to_excel_returns_none_without_tables():
    assert markdown_tables_to_excel("没有任何表格") is None


def test_kie_to_excel():
    data = kie_to_excel([{"商户": "小米", "金额": 99.0}])
    df = pd.read_excel(io.BytesIO(data))
    assert df.iloc[0]["商户"] == "小米"
