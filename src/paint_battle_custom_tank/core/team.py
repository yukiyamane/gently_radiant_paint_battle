"""チーム単位の戦車管理モジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING
from paint_battle_custom_tank.core.setting import TeamSettingFactory, TeamType
from paint_battle_custom_tank.core.tank import Tank

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.main import MyApp


class Team:
    """チームに所属する戦車の生成および更新を管理するクラス。"""

    def __init__(self, base: MyApp, battle: Battle, team_type: TeamType) -> None:
        self.__team_type = team_type
        self.__tank_list: list[Tank] = []
        team_setting = TeamSettingFactory.create(team_type)
        tank = Tank(
            base,
            battle,
            team_type,
            team_setting.tank_main_weapon_type,
            team_setting.tank_sub_weapon_type,
            team_setting.tank_special_weapon_type,
        )
        self.__tank_list.append(tank)

    @property
    def team_type(self) -> TeamType:
        return self.__team_type

    @property
    def tank_list(self) -> list[Tank]:
        return self.__tank_list

    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        """物理演算前の更新（入力を受けて弾丸発射など）"""
        for tank in self.__tank_list:
            tank.pre_physics_update(current_raw_time, dt)

    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        """物理演算後の更新（位置の更新、グラフィックスの更新など）"""
        for tank in self.__tank_list:
            tank.post_physics_update(current_raw_time, dt)

    def disable_input(self) -> None:
        """試合終了時に全戦車の入力を禁止する（物理演算用のフラグを落とすなど）"""
        for tank in self.__tank_list:
            tank.disable_input()