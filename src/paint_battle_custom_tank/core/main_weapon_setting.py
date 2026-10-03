"""メイン・サブ武器パラメータ設定モジュール。"""

from __future__ import annotations
from dataclasses import dataclass, field
# pyrefly: ignore [missing-import]
from panda3d.core import Vec3
from paint_battle_custom_tank.core.paint import BrushType
from paint_battle_custom_tank.core.setting import WeaponType
from paint_battle_custom_tank.graphics.setting import Language

@dataclass(frozen=True)
class SplashSetting:
    """着弾・中間飛沫・足元インクのサイズおよびブラシ設定。

    Attributes
    ----------
    foot_radius : float
        発射時の足元インク半径（メートル）。
    foot_pattern : tuple[bool, ...]
        足元インクの発生パターン（Trueで発生）。
    foot_brush_type : BrushType
        足元インクのブラシ種別。
    mid_radius : float
        飛翔中インク滴の半径（メートル）。
    mid_distance : float
        飛翔中インク滴の発生間隔（メートル）。
    mid_brush_type : BrushType
        飛翔中インク滴のブラシ種別。
    impact_radius : float
        着弾インクの半径（メートル）。
    impact_brush_type : BrushType
        着弾インクのブラシ種別。
    """

    foot_radius: float
    foot_pattern: tuple[bool, ...]
    foot_brush_type: BrushType
    mid_radius: float
    mid_distance: float
    mid_brush_type: BrushType
    impact_radius: float
    impact_brush_type: BrushType


@dataclass(frozen=True)
class WeaponSetting:
    """武器のUI表示情報。"""

    image_file_name: str
    name_dict: dict[Language, str]


@dataclass(frozen=True)
class BounceSetting:
    """バウンス弾（跳ね返り弾）の設定パラメータ。"""

    battery_radius: float
    radius: float
    damage: int
    fire_interval: float
    bullet_speed: float
    bullet_range: float
    max_bounce: int
    splash_setting: SplashSetting
    image_file_name: str = "bounce"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "跳ね返る弾", Language.ENG: "Bouncing Bullet"}
    )

    @classmethod
    def main_weapon(cls) -> BounceSetting:
        return cls(
            battery_radius=10.0,
            radius=3.0,
            damage=70,
            fire_interval=0.5,
            bullet_speed=100.0,
            bullet_range=600.0,
            max_bounce=2,
            splash_setting=SplashSetting(
                foot_radius=2.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=3.0,
                mid_distance=50.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=5.0,
                impact_brush_type=BrushType.STRETCHED,
            ),
        )

    @classmethod
    def sub_weapon(cls) -> BounceSetting:
        return cls(
            battery_radius=3.0,
            radius=2.0,
            damage=50,
            fire_interval=1.25,
            bullet_speed=100.0,
            bullet_range=300.0,
            max_bounce=1,
            splash_setting=SplashSetting(
                foot_radius=1.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=2.0,
                mid_distance=50.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=3.0,
                impact_brush_type=BrushType.STRETCHED,
            ),
        )


@dataclass(frozen=True)
class ExplodingSetting:
    """爆発弾の設定パラメータ。"""

    battery_radius: float
    radius: float
    direct_damage: int
    explosion_damage: int
    fire_interval: float
    bullet_speed: float
    bullet_range: float
    explosion_radius: float
    splash_setting: SplashSetting
    image_file_name: str = "exploding"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "爆発する弾", Language.ENG: "Exploding Bullet"}
    )

    @classmethod
    def main_weapon(cls) -> ExplodingSetting:
        return cls(
            battery_radius=10.0,
            radius=5.0,
            direct_damage=100,
            explosion_damage=200,
            fire_interval=2.0,
            bullet_speed=100.0,
            bullet_range=400.0,
            explosion_radius=18.0,
            splash_setting=SplashSetting(
                foot_radius=2.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=4.0,
                mid_distance=8.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=18.0,
                impact_brush_type=BrushType.BIG_NOISED_CIRCLE,
            ),
        )

    @classmethod
    def sub_weapon(cls) -> ExplodingSetting:
        return cls(
            battery_radius=3.0,
            radius=3.0,
            direct_damage=30,
            explosion_damage=70,
            fire_interval=5.0,
            bullet_speed=100.0,
            bullet_range=300.0,
            explosion_radius=10.0,
            splash_setting=SplashSetting(
                foot_radius=1.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=2.0,
                mid_distance=4.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=10.0,
                impact_brush_type=BrushType.BIG_NOISED_CIRCLE,
            ),
        )


@dataclass(frozen=True)
class ThreeWaySetting:
    """3方向拡散弾の設定パラメータ。"""

    battery_radius: float
    radius: float
    damage: int
    fire_interval: float
    bullet_speed: float
    bullet_range: float
    left_direction_angle: float
    left_pos_offset: Vec3
    right_direction_angle: float
    right_pos_offset: Vec3
    splash_setting: SplashSetting
    image_file_name: str = "three_way"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "三方向の弾", Language.ENG: "3-Way Bullet"}
    )

    @classmethod
    def main_weapon(cls) -> ThreeWaySetting:
        return cls(
            battery_radius=10.0,
            radius=3.0,
            damage=50,
            fire_interval=0.8,
            bullet_speed=100.0,
            bullet_range=600.0,
            left_direction_angle=-10.0,
            left_pos_offset=Vec3(4, 1, 0),
            right_direction_angle=10.0,
            right_pos_offset=Vec3(-4, 1, 0),
            splash_setting=SplashSetting(
                foot_radius=2.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=3.0,
                mid_distance=50.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=4.0,
                impact_brush_type=BrushType.STRETCHED,
            ),
        )

    @classmethod
    def sub_weapon(cls) -> ThreeWaySetting:
        return cls(
            battery_radius=3.0,
            radius=2.0,
            damage=30,
            fire_interval=2.3,
            bullet_speed=100.0,
            bullet_range=600.0,
            left_direction_angle=-5.0,
            left_pos_offset=Vec3(1.6, 0.5, 0),
            right_direction_angle=5.0,
            right_pos_offset=Vec3(-1.6, 0.5, 0),
            splash_setting=SplashSetting(
                foot_radius=1.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=2.0,
                mid_distance=50.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=3.0,
                impact_brush_type=BrushType.STRETCHED,
            ),
        )


@dataclass(frozen=True)
class LaserSetting:
    """レーザー（高速貫通光線）の設定パラメータ。"""

    battery_radius: float
    radius: float
    damage: int
    fire_interval: float
    bullet_speed: float
    bullet_range: float
    knockback: float
    splash_setting: SplashSetting
    image_file_name: str = "laser"
    name_dict: dict[Language, str] = field(
        default_factory=lambda: {Language.JPN: "光線", Language.ENG: "Laser"}
    )

    @classmethod
    def main_weapon(cls) -> LaserSetting:
        return cls(
            battery_radius=10.0,
            radius=2.0,
            damage=120,
            fire_interval=1.0,
            bullet_speed=800.0,
            bullet_range=300.0,
            knockback=100.0,
            splash_setting=SplashSetting(
                foot_radius=1.0,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=3.0,
                mid_distance=4.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=4.0,
                impact_brush_type=BrushType.STRETCHED,
            ),
        )

    @classmethod
    def sub_weapon(cls) -> LaserSetting:
        return cls(
            battery_radius=3.0,
            radius=1.0,
            damage=50,
            fire_interval=2.4,
            bullet_speed=600.0,
            bullet_range=200.0,
            knockback=50.0,
            splash_setting=SplashSetting(
                foot_radius=0.5,
                foot_pattern=(True, False),
                foot_brush_type=BrushType.NOISED_CIRCLE,
                mid_radius=2.0,
                mid_distance=3.0,
                mid_brush_type=BrushType.NOISED_CIRCLE,
                impact_radius=3.0,
                impact_brush_type=BrushType.STRETCHED,
            ),
        )


class WeaponSettingFactory:
    """メイン/サブ武器の設定オブジェクトを取得するファクトリ。"""

    MAIN = {
        WeaponType.BOUNCE: BounceSetting.main_weapon,
        WeaponType.THREE_WAY: ThreeWaySetting.main_weapon,
        WeaponType.EXPLODING: ExplodingSetting.main_weapon,
        WeaponType.LASER: LaserSetting.main_weapon,
    }

    SUB = {
        WeaponType.BOUNCE: BounceSetting.sub_weapon,
        WeaponType.THREE_WAY: ThreeWaySetting.sub_weapon,
        WeaponType.EXPLODING: ExplodingSetting.sub_weapon,
        WeaponType.LASER: LaserSetting.sub_weapon,
    }

    @classmethod
    def main(cls, weapon_type: WeaponType):
        """メイン武器設定を生成する。"""
        return cls.MAIN[weapon_type]()

    @classmethod
    def sub(cls, weapon_type: WeaponType):
        """サブ武器設定を生成する。"""
        return cls.SUB[weapon_type]()