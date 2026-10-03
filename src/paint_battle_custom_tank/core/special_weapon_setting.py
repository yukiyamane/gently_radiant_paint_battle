"""スペシャル武器パラメータ設定モジュール。"""

from __future__ import annotations
from dataclasses import dataclass, field
from paint_battle_custom_tank.core.paint import BrushType
from paint_battle_custom_tank.core.setting import SpecialWeaponType
from paint_battle_custom_tank.graphics.setting import Language

@dataclass(frozen=True)
class SpecialWeaponSetting:
    """スペシャル武器のベース設定データクラス。"""

    image_file_name: str
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "", Language.ENG: ""}
    )


@dataclass(frozen=True)
class MissileSetting(SpecialWeaponSetting):
    """ミサイル（誘導弾）の設定パラメータ。"""

    distance_tuple: tuple[float, ...] = field(default_factory=lambda: (5.0, 10.0, 15.0))
    damage_tuple: tuple[int, ...] = field(default_factory=lambda: (300, 100, 50))
    radius: float = 2.0
    brush_type: BrushType = BrushType.BIG_NOISED_CIRCLE
    paint_radius: float = 20.0

    splash_paint_radius: float = 4.0
    splash_paint_distance: float = 25.0
    num_splash: int = 6
    splash_brush_type: BrushType = BrushType.STRETCHED 

    fire_interval: float = 0.5
    ascend_speed: float = 10.0
    ascend_height: float = 50.0
    move_speed: float = 10.0
    drop_speed: float = 40.0
    explosion_radius: float = 20.0
    explosion_damage: int = 300
    image_file_name: str = "missile"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "誘導弾", Language.ENG: "Missile"}
    )


@dataclass(frozen=True)
class RainSetting(SpecialWeaponSetting):
    """雨ふらし（インクの雨）の設定パラメータ。"""

    radius: float = 60.0
    move_speed: float = 20.0
    damage_interval: float = 0.5
    damage_per_interval: int = 50
    duration: float = 8.0
    number_of_drop_per_second: int = 72
    rain_drop_radius: tuple[float, float] = (0.1, 0.1)
    brush_type: BrushType = BrushType.NOISED_CIRCLE
    paint_radius: float = 2.0
    image_file_name: str = "rain"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "雨", Language.ENG: "Rain"}
    )


@dataclass(frozen=True)
class ElectromagneticWaveSetting(SpecialWeaponSetting):
    """電磁波（EMP）の設定パラメータ。"""

    max_radius: float = 300.0
    expand_speed: float = 40.0
    damage: int = 450
    image_file_name: str = "electromagnetic_wave"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "電磁波", Language.ENG: "EMP"}
    )


@dataclass(frozen=True)
class HyperBeamSetting(SpecialWeaponSetting):
    """破壊光線（ハイパービーム）の設定パラメータ。"""

    radius: float = 15.0
    bullet_range: float = 400.0
    number_of_drop_per_second: int = 96
    brush_type: BrushType = BrushType.NOISED_CIRCLE
    paint_radius: float = 3.0
    damage_interval: float = 0.25
    damage_per_interval: int = 180
    duration: float = 4.0
    image_file_name: str = "hyper_beam"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "破壊光線", Language.ENG: "Hyper Beam"}
    )


class SpecialWeaponSettingFactory:
    """スペシャル武器設定を生成するファクトリ。"""

    @classmethod
    def create(cls, special_weapon_type: SpecialWeaponType) -> SpecialWeaponSetting:
        """指定されたスペシャル武器種別の設定インスタンスを取得する。"""
        if special_weapon_type is SpecialWeaponType.MISSILE:
            return MissileSetting()
        elif special_weapon_type is SpecialWeaponType.RAIN:
            return RainSetting()
        elif special_weapon_type is SpecialWeaponType.ELECTROMAGNETIC_WAVE:
            return ElectromagneticWaveSetting()
        elif special_weapon_type is SpecialWeaponType.HYPER_BEAM:
            return HyperBeamSetting()
        else:
            raise ValueError(f"Invalid special_weapon_type: {special_weapon_type}")