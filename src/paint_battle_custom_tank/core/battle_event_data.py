"""バトル内イベントデータクラス定義モジュール。"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
# pyrefly: ignore [missing-import]
from panda3d.core import Vec3

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.paint import BrushType
    from paint_battle_custom_tank.core.setting import TeamType
    from paint_battle_custom_tank.core.tank import Tank


@dataclass(frozen=True)
class DamageEvent:
    """ダメージ発生イベントデータ。

    Attributes
    ----------
    attacker : Tank
        攻撃を行った戦車。
    amount : int
        ダメージ量。
    attacker_team : TeamType
        攻撃側のチーム。
    """

    attacker: Tank
    amount: int
    attacker_team: TeamType


@dataclass(frozen=True)
class PaintEvent:
    """地面インク塗布要求イベントデータ。

    Attributes
    ----------
    requester : Tank
        塗布を要求した戦車。
    brush_type : BrushType
        使用するブラシ形状種別。
    pos : Vec3
        塗布中心のワールド座標。
    brush_world_radius : float
        ブラシのワールド半径（メートル）。
    direction : Vec3
        ブラシの進行・回転方向ベクトル。
    team_type : TeamType
        塗布する色に対応するチーム。
    """

    requester: Tank
    brush_type: BrushType
    pos: Vec3
    brush_world_radius: float
    direction: Vec3
    team_type: TeamType
