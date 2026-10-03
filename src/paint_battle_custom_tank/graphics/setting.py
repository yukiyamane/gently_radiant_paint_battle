"""グラフィックス・UI設定モジュール。"""

from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
# pyrefly: ignore [missing-import]
from panda3d.core import Material
from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.graphics.material import (
    ColorData,
    ColorStorage,
    MaterialFactory,
    MaterialStorage
)


class Language(Enum):
    ENG = auto()
    JPN = auto()


class HUDTextKey(Enum):
    """UIローカライズ用テキストキー。"""

    MAIN_WEAPON_PREFIX = auto()
    SUB_WEAPON_PREFIX = auto()
    SPECIAL_WEAPON_PREFIX = auto()
    READY = auto()
    GO = auto()
    FINISH = auto()
    WINNER_PREFIX = auto()
    PAINT_LABEL = auto()
    ELIMS_LABEL = auto()
    DEATHS_LABEL = auto()
    SPECIALS_LABEL = auto()


HUD_STRINGS: dict[HUDTextKey, dict[Language, str]] = {
    HUDTextKey.MAIN_WEAPON_PREFIX: {Language.ENG: "Main", Language.JPN: "主砲"},
    HUDTextKey.SUB_WEAPON_PREFIX: {Language.ENG: "Sub", Language.JPN: "副砲"},
    HUDTextKey.SPECIAL_WEAPON_PREFIX: {Language.ENG: "Special", Language.JPN: "必殺砲"},
    HUDTextKey.READY: {Language.ENG: "Ready...", Language.JPN: "ようい..."},
    HUDTextKey.GO: {Language.ENG: "Go!", Language.JPN: "どん！"},
    HUDTextKey.FINISH: {Language.ENG: "Finish!", Language.JPN: "おしまい！"},
    HUDTextKey.WINNER_PREFIX: {Language.ENG: "Winner: ", Language.JPN: "勝者: "},
    HUDTextKey.PAINT_LABEL: {Language.ENG: "Paint: ", Language.JPN: "塗った: "},
    HUDTextKey.ELIMS_LABEL: {Language.ENG: "Elims: ", Language.JPN: "たおした: "},
    HUDTextKey.DEATHS_LABEL: {Language.ENG: "Deaths: ", Language.JPN: "やられた: "},
    HUDTextKey.SPECIALS_LABEL: {Language.ENG: "Specials: ", Language.JPN: "必殺した: "},
}


@dataclass(frozen=True)
class TeamGraphicsSetting:
    """チームごとのグラフィックス表示（色・マテリアル・表示名）設定。

    Attributes
    ----------
    name_dict : dict[Language, str]
        言語別チーム表示名。
    paint_color : ColorData
        通常インク色。
    paint_color_light : ColorData
        ハイライト・エフェクト用インク色。
    bullet_material : Material
        弾丸用マテリアル。
    tank_mid_material : Material
        戦車本体中間色マテリアル。
    tank_light_material : Material
        戦車本体明色マテリアル。
    tank_dark_material : Material
        戦車本体暗色マテリアル。
    """

    name_dict: dict[Language, str]
    paint_color: ColorData
    paint_color_light: ColorData
    bullet_material: Material
    tank_mid_material: Material
    tank_light_material: Material
    tank_dark_material: Material

    def get_name(self, language: Language) -> str:
        """指定された言語でのチーム表示名を取得する。"""
        return self.name_dict.get(language, "")


@dataclass(frozen=True)
class GraphicsSetting:
    """グラフィックス全体設定。

    Attributes
    ----------
    language : Language
        UI表示言語。
    teams : dict[TeamType, TeamGraphicsSetting]
        チーム別グラフィックス設定の辞書。
    """

    language: Language = Language.ENG
    teams: dict[TeamType, TeamGraphicsSetting] = field(default_factory=dict)

    @property
    def alpha(self) -> TeamGraphicsSetting:
        """アルファチーム用グラフィックス設定。"""
        return self.teams[TeamType.ALPHA]

    @property
    def bravo(self) -> TeamGraphicsSetting:
        """ブラボーチーム用グラフィックス設定。"""
        return self.teams[TeamType.BRAVO]

    def get_team(self, team_type: TeamType) -> TeamGraphicsSetting:
        """指定されたチームのグラフィックス設定を取得する。"""
        if team_type not in self.teams:
            raise ValueError(f"Invalid team_type: {team_type}")
        return self.teams[team_type]

    def get_team_setting(self, team_type: TeamType) -> TeamGraphicsSetting:
        """指定されたチームのグラフィックス設定を取得する（後方互換用エイリアス）。"""
        return self.get_team(team_type)

    def get_text(self, key: HUDTextKey) -> str:
        """現在の言語設定に応じたローカライズ文字列を取得する。"""
        return HUD_STRINGS.get(key, {}).get(self.language, "")



color_orange = TeamGraphicsSetting(
    name_dict={Language.ENG: "Orange", Language.JPN: "だいだい"},
    paint_color=ColorStorage.ink_orange,
    paint_color_light=ColorStorage.ink_orange_light,
    bullet_material=MaterialStorage.ink_orange_light_diff,
    tank_mid_material=MaterialStorage.ink_orange_diff,
    tank_light_material=MaterialStorage.ink_orange_light_diff,
    tank_dark_material=MaterialStorage.ink_orange_dark_diff,
)
color_blue = TeamGraphicsSetting(
    name_dict={Language.ENG: "Blue", Language.JPN: "あお"},
    paint_color=ColorStorage.ink_blue,
    paint_color_light=ColorStorage.ink_blue_light,
    bullet_material=MaterialStorage.ink_blue_light_diff,
    tank_mid_material=MaterialStorage.ink_blue_diff,
    tank_light_material=MaterialStorage.ink_blue_light_diff,
    tank_dark_material=MaterialStorage.ink_blue_dark_diff,
)
color_green = TeamGraphicsSetting(
    name_dict={Language.ENG: "Green", Language.JPN: "みどり"},
    paint_color=ColorStorage.ink_green,
    paint_color_light=ColorStorage.ink_green_light,
    bullet_material=MaterialStorage.ink_green_light_diff,
    tank_mid_material=MaterialStorage.ink_green_diff,
    tank_light_material=MaterialStorage.ink_green_light_diff,
    tank_dark_material=MaterialStorage.ink_green_dark_diff,
)
color_pink = TeamGraphicsSetting(
    name_dict={Language.ENG: "Pink", Language.JPN: "もも"},
    paint_color=ColorStorage.ink_pink,
    paint_color_light=ColorStorage.ink_pink_light,
    bullet_material=MaterialStorage.ink_pink_light_diff,
    tank_mid_material=MaterialStorage.ink_pink_diff,
    tank_light_material=MaterialStorage.ink_pink_light_diff,
    tank_dark_material=MaterialStorage.ink_pink_dark_diff,
)


# アルファチーム（オレンジ系）グラフィックス設定
alpha_graphics: TeamGraphicsSetting = color_blue

# ブラボーチーム（ブルー系）グラフィックス設定
bravo_graphics: TeamGraphicsSetting = color_pink

team_graphics_registry: dict[TeamType, TeamGraphicsSetting] = {
    TeamType.ALPHA: alpha_graphics,
    TeamType.BRAVO: bravo_graphics,
}

graphics_setting: GraphicsSetting = GraphicsSetting(
    language=Language.ENG,
    teams={
        TeamType.ALPHA: alpha_graphics,
        TeamType.BRAVO: bravo_graphics,
    },
)