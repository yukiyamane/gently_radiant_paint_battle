"""武器状態列挙型定義モジュール。"""

from __future__ import annotations
from enum import Enum, auto


class WeaponMode(Enum):
    """武器の発射制御モード。"""

    READY = auto()       # 発射可能状態
    SUPPRESSED = auto()  # 発射抑制状態（リスポーン待機中など）
