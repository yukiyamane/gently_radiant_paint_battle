"""バトル設定およびチームパラメータ定義モジュール。"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class TeamType(Enum):
    """チーム識別列挙型。"""

    ALPHA = auto()
    BRAVO = auto()


class WeaponType(Enum):
    """メイン/サブ武器種別列挙型。"""

    BOUNCE = auto()
    EXPLODING = auto()
    THREE_WAY = auto()
    LASER = auto()


class SpecialWeaponType(Enum):
    """スペシャル武器種別列挙型。"""

    MISSILE = auto()
    RAIN = auto()
    ELECTROMAGNETIC_WAVE = auto()
    HYPER_BEAM = auto()


@dataclass(frozen=True)
class BattleSetting:
    """試合全体のルール・制限時間設定。

    Attributes
    ----------
    game_duration : float
        試合本編の制限時間（秒）。
    pre_game_duration : float
        試合開始前のカウントダウン時間（秒）。
    """

    game_duration: float = 180.0
    pre_game_duration: float = 3.0


@dataclass(frozen=True)
class TankSetting:
    """戦車の基本パラメータ設定。"""

    respawn_time: float = 10.0


class TeamSettingFactory:
    """チーム設定を生成するファクトリクラス（後方互換性用）。"""

    @staticmethod
    def create(team_type: TeamType) -> TeamSetting:
        """指定されたチームの装備設定を取得する。"""
        return TeamSetting.get(team_type)




@dataclass(frozen=True)
class TeamSetting:
    """各チームの戦車装備構成設定。

    Attributes
    ----------
    team_type : TeamType
        所属チーム。
    tank_main_weapon_type : WeaponType
        メイン武器種別。
    tank_sub_weapon_type : WeaponType
        サブ武器種別。
    tank_special_weapon_type : SpecialWeaponType
        スペシャル武器種別。
    """

    team_type: TeamType
    tank_main_weapon_type: WeaponType
    tank_sub_weapon_type: WeaponType
    tank_special_weapon_type: SpecialWeaponType

    @classmethod
    def alpha(cls) -> TeamSetting:
        """アルファチームの標準装備設定を生成する。"""
        return color_blue

    @classmethod
    def bravo(cls) -> TeamSetting:
        """ブラボーチームの標準装備設定を生成する。"""
        return color_pink

    @classmethod
    def get(cls, team_type: TeamType) -> TeamSetting:
        """指定されたチームの装備設定を取得する。"""
        if team_type is TeamType.ALPHA:
            return cls.alpha()
        elif team_type is TeamType.BRAVO:
            return cls.bravo()
        else:
            raise ValueError(f"Invalid team_type: {team_type}")


color_blue = TeamSetting(
            team_type=TeamType.ALPHA,
            tank_main_weapon_type=WeaponType.EXPLODING,
            tank_sub_weapon_type=WeaponType.THREE_WAY,
            tank_special_weapon_type=SpecialWeaponType.MISSILE,
)

color_green = TeamSetting(
            team_type=TeamType.BRAVO,
            tank_main_weapon_type=WeaponType.THREE_WAY,
            tank_sub_weapon_type=WeaponType.LASER,
            tank_special_weapon_type=SpecialWeaponType.RAIN,
)

color_pink = TeamSetting(
    TeamType.BRAVO,
    tank_main_weapon_type=WeaponType.BOUNCE,
    tank_sub_weapon_type=WeaponType.EXPLODING,
    tank_special_weapon_type=SpecialWeaponType.ELECTROMAGNETIC_WAVE,
)

color_orange = TeamSetting(
    TeamType.BRAVO,
    tank_main_weapon_type=WeaponType.LASER,
    tank_sub_weapon_type=WeaponType.BOUNCE,
    tank_special_weapon_type=SpecialWeaponType.HYPER_BEAM,
)


battle_setting: BattleSetting = BattleSetting()
tank_setting: TankSetting = TankSetting()