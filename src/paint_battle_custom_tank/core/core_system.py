"""コアゲームシステムの最上位ラッパークラスモジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING
from paint_battle_custom_tank.core.battle import Battle

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


class CoreSystem:
    """バトルロジックを統括・更新するコアシステム。"""

    def __init__(self, base: MyApp) -> None:
        self.__battle: Battle = Battle(base)

    @property
    def battle(self) -> Battle:
        return self.__battle

    def update(self, current_raw_time: float, dt: float) -> None:
        """毎フレームのコアシステム更新。"""
        self.__battle.update(current_raw_time, dt)
