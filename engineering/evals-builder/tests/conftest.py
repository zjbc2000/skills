"""让 tests 能找到 scripts/ 下的模块（scripts 无 __init__.py，脚本式导入）。"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
