"""共通ロギングおよび基本設定モジュール。"""

from __future__ import annotations
import logging
# pyrefly: ignore [missing-import]
from panda3d.core import ClockObject

# ロガーの初期化
logger: logging.Logger = logging.getLogger("paint_battle_custom_tank")
_handler: logging.StreamHandler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_formatter: logging.Formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)
_handler.setFormatter(_formatter)

if not logger.handlers:
    logger.addHandler(_handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False

# グローバルクロック
globalClock: ClockObject = ClockObject.getGlobalClock()
