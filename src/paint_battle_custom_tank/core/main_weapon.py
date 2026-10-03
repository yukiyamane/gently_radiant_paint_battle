"""メインおよびサブ武器の発射制御・弾丸生成管理モジュール。"""

from __future__ import annotations
import math
from typing import TYPE_CHECKING, override
# pyrefly: ignore [missing-import]
from panda3d.core import Vec3

from paint_battle_custom_tank.core.main_bullet import (
    BounceBullet,
    ExplodingBullet,
    LaserBullet,
    ThreeWayBullet,
)
from paint_battle_custom_tank.core.main_weapon_setting import (
    BounceSetting,
    ExplodingSetting,
    LaserSetting,
    ThreeWaySetting,
)
from paint_battle_custom_tank.core.setting import TeamType, WeaponType
from paint_battle_custom_tank.core.weapon import WeaponMode

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import Tank
    from paint_battle_custom_tank.main import MyApp


class WeaponFactory:
    """メイン/サブ武器インスタンスを生成するファクトリ。"""

    @staticmethod
    def create_main(
        weapon_type: WeaponType,
        base: MyApp,
        battle: Battle,
        tank: Tank,
        team_type: TeamType,
    ) -> Weapon:
        """メイン武器を生成する。"""
        if weapon_type is WeaponType.BOUNCE:
            return BounceWeapon(base, battle, tank, team_type, BounceSetting.main_weapon())
        elif weapon_type is WeaponType.EXPLODING:
            return ExplodingWeapon(base, battle, tank, team_type, ExplodingSetting.main_weapon())
        elif weapon_type is WeaponType.THREE_WAY:
            return ThreeWayWeapon(base, battle, tank, team_type, ThreeWaySetting.main_weapon())
        elif weapon_type is WeaponType.LASER:
            return LaserWeapon(base, battle, tank, team_type, LaserSetting.main_weapon())
        else:
            raise ValueError(f"Unknown weapon type: {weapon_type}")

    @staticmethod
    def create_sub(
        weapon_type: WeaponType,
        base: MyApp,
        battle: Battle,
        tank: Tank,
        team_type: TeamType,
    ) -> Weapon:
        """サブ武器を生成する。"""
        if weapon_type is WeaponType.BOUNCE:
            return BounceWeapon(base, battle, tank, team_type, BounceSetting.sub_weapon())
        elif weapon_type is WeaponType.EXPLODING:
            return ExplodingWeapon(base, battle, tank, team_type, ExplodingSetting.sub_weapon())
        elif weapon_type is WeaponType.THREE_WAY:
            return ThreeWayWeapon(base, battle, tank, team_type, ThreeWaySetting.sub_weapon())
        elif weapon_type is WeaponType.LASER:
            return LaserWeapon(base, battle, tank, team_type, LaserSetting.sub_weapon())
        else:
            raise ValueError(f"Unknown weapon type: {weapon_type}")


class Weapon:
    """武器の抽象基底クラス。"""

    def set_mode(self, weapon_mode: WeaponMode) -> None:
        """発射制御モード（READY / SUPPRESSED）を設定する。"""
        raise NotImplementedError

    def pre_physics_update(
        self, current_raw_time: float, dt: float, pos: Vec3, direction: Vec3
    ) -> None:
        """物理ステップ前の更新。"""
        raise NotImplementedError

    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        """物理ステップ後の更新。"""
        raise NotImplementedError


class BounceWeapon(Weapon):
    """バウンス弾発射装置。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        team_type: TeamType,
        setting: BounceSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = setting
        self.__fire_interval = setting.fire_interval
        self.__bullet_list: list[BounceBullet] = []
        self.__timer = 0.0
        self.__bullet_index = 0
        self.__mode = WeaponMode.READY

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float, pos: Vec3, direction: Vec3) -> None:
        self.__timer -= dt
        if self.__timer <= 0:
            if self.__mode is WeaponMode.READY:
                bullet = BounceBullet(
                    self.__base,
                    self.__battle,
                    self.__tank_ref,
                    self.__bullet_index,
                    self.__team_type,
                    self.__setting,
                    pos,
                    direction,
                )
                self.__bullet_list.append(bullet)
                self.__bullet_index += 1
                self.__timer += self.__fire_interval
            elif self.__mode is WeaponMode.SUPPRESSED:
                self.__timer = 0.0
        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_dead]



        


class ExplodingWeapon(Weapon):
    """爆発弾発射装置。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        team_type: TeamType,
        setting: ExplodingSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = setting
        self.__fire_interval = setting.fire_interval
        self.__bullet_list: list[ExplodingBullet] = []
        self.__bullet_index = 0
        self.__timer = 0.0
        self.__mode = WeaponMode.READY

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(
        self, current_raw_time: float, dt: float, pos: Vec3, direction: Vec3
    ) -> None:
        self.__timer -= dt
        if self.__timer <= 0:
            if self.__mode is WeaponMode.READY:
                bullet = ExplodingBullet(
                    self.__base,
                    self.__battle,
                    self.__tank_ref,
                    self.__bullet_index,
                    self.__team_type,
                    self.__setting,
                    pos,
                    direction,
                )
                self.__bullet_list.append(bullet)
                self.__bullet_index += 1
                self.__timer += self.__fire_interval
            elif self.__mode is WeaponMode.SUPPRESSED:
                self.__timer = 0.0
        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_dead]


class ThreeWayWeapon(Weapon):
    """3方向拡散弾発射装置。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        team_type: TeamType,
        setting: ThreeWaySetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = setting
        self.__fire_interval = setting.fire_interval
        self.__bullet_list: list[ThreeWayBullet] = []
        self.__timer = 0.0
        self.__bullet_index = 0
        self.__mode = WeaponMode.READY

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(
        self, current_raw_time: float, dt: float, pos: Vec3, direction: Vec3
    ) -> None:
        self.__timer -= dt
        if self.__timer <= 0:
            if self.__mode is WeaponMode.READY:
                pos_center = pos + direction * self.__setting.battery_radius
                direction_center = direction

                pos_offset_right = self.__local_to_world_offset(
                    self.__setting.right_pos_offset, direction
                )
                pos_offset_left = self.__local_to_world_offset(
                    self.__setting.left_pos_offset, direction
                )

                direction_right = self.__rotate_z(
                    direction, self.__setting.right_direction_angle
                )
                pos_right = (
                    pos
                    + direction_right * self.__setting.battery_radius
                    + pos_offset_right
                )

                direction_left = self.__rotate_z(
                    direction, self.__setting.left_direction_angle
                )
                pos_left = (
                    pos
                    + direction_left * self.__setting.battery_radius
                    + pos_offset_left
                )

                bullet_center = ThreeWayBullet(
                    self.__base,
                    self.__battle,
                    self.__tank_ref,
                    self.__bullet_index,
                    self.__team_type,
                    self.__setting,
                    pos_center,
                    direction_center,
                )
                self.__bullet_list.append(bullet_center)
                bullet_right = ThreeWayBullet(
                    self.__base,
                    self.__battle,
                    self.__tank_ref,
                    self.__bullet_index,
                    self.__team_type,
                    self.__setting,
                    pos_right,
                    direction_right,
                )
                self.__bullet_list.append(bullet_right)
                bullet_left = ThreeWayBullet(
                    self.__base,
                    self.__battle,
                    self.__tank_ref,
                    self.__bullet_index,
                    self.__team_type,
                    self.__setting,
                    pos_left,
                    direction_left,
                )
                self.__bullet_list.append(bullet_left)
                self.__bullet_index += 1

                self.__timer += self.__fire_interval
            elif self.__mode is WeaponMode.SUPPRESSED:
                self.__timer = 0.0

        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_dead]

    def __rotate_z(self, v: Vec3, deg: float) -> Vec3:
        x, y, z = v
        th = math.radians(deg)
        x2 = x * math.cos(th) - y * math.sin(th)
        y2 = x * math.sin(th) + y * math.cos(th)
        return Vec3(x2, y2, z)

    def __local_to_world_offset(self, offset: Vec3, forward: Vec3) -> Vec3:
        f = forward.normalized()
        right = Vec3(f.y, -f.x, 0)
        return right * offset.x + f * offset.y


class LaserWeapon(Weapon):
    """レーザー発射装置。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        team_type: TeamType,
        setting: LaserSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = setting
        self.__fire_interval = setting.fire_interval
        self.__bullet_list: list[LaserBullet] = []
        self.__timer = 0.0
        self.__bullet_index = 0
        self.__mode = WeaponMode.READY

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(
        self, current_raw_time: float, dt: float, pos: Vec3, direction: Vec3
    ) -> None:
        self.__timer -= dt
        if self.__timer <= 0:
            if self.__mode is WeaponMode.READY:
                bullet_pos = pos + direction * self.__setting.battery_radius
                bullet = LaserBullet(
                    self.__base,
                    self.__battle,
                    self.__tank_ref,
                    self.__bullet_index,
                    self.__team_type,
                    self.__setting,
                    bullet_pos,
                    direction,
                )
                self.__bullet_list.append(bullet)
                self.__bullet_index += 1
                self.__timer += self.__fire_interval
            elif self.__mode is WeaponMode.SUPPRESSED:
                self.__timer = 0.0

        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_dead]
