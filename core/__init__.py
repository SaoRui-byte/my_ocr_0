"""core 包初始化：把官方仓库 vendor 目录加入 sys.path，复用 postprocess / evaluation_pipeline。"""
import sys
from pathlib import Path

_THIRD_PARTY = Path(__file__).resolve().parent.parent / "third_party" / "Xiaomi-OCR-0"
if str(_THIRD_PARTY) not in sys.path:
    sys.path.insert(0, str(_THIRD_PARTY))
