"""使 pytest 从仓库根可导入 backend 包（本项目无 packaging）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
