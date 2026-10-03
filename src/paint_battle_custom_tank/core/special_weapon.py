"""スペシャル武器の発動制御および弾丸管理モジュール。"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, override, Optional
# pyrefly: ignore [missing-import]
from panda3d.core import Point3, Vec3

from paint_battle_custom_tank.core.setting import SpecialWeaponType, TeamType
from paint_battle_custom_tank.core.special_bullet import (
    ElectromagneticWaveBullet,
    HyperBeamBullet,
    MissileBullet,
    RainBullet,
)
from paint_battle_custom_tank.core.special_weapon_setting import (
    ElectromagneticWaveSetting,
    HyperBeamSetting,
    MissileSetting,
    RainSetting,
)
from paint_battle_custom_tank.core.weapon import WeaponMode
from paint_battle_custom_tank.graphics.special_bullet import ShuwaShuwaGraphics, RainUpdraftGraphics, HyperBeamBulletPreGraphics
from paint_battle_custom_tank.shared.util.yamane_state_machine import (
    StateContext,
    StateMachine,
)


if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import Tank
    from paint_battle_custom_tank.main import MyApp


class SpecialWeaponFactory:
    """スペシャル武器インスタンスを生成するファクトリ。"""

    @staticmethod
    def create(
        weapon_type: SpecialWeaponType,
        base: MyApp,
        battle: Battle,
        owner: Tank,
        team_type: TeamType,
    ) -> SpecialWeapon:
        """スペシャル武器を生成する。"""
        if weapon_type is SpecialWeaponType.MISSILE:
            return Missile(base, battle, owner, team_type, MissileSetting())
        elif weapon_type is SpecialWeaponType.RAIN:
            return Rain(base, battle, owner, team_type, RainSetting())
        elif weapon_type is SpecialWeaponType.ELECTROMAGNETIC_WAVE:
            return ElectromagneticWave(
                base, battle, owner, team_type, ElectromagneticWaveSetting()
            )
        elif weapon_type is SpecialWeaponType.HYPER_BEAM:
            return HyperBeam(base, battle, owner, team_type, HyperBeamSetting())
        else:
            raise NotImplementedError(f"{weapon_type} は未実装の特殊武器です。")


class SpecialWeapon(ABC):
    """スペシャル武器の抽象基底クラス。"""

    @abstractmethod
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        """発射制御モードを設定する。"""
        pass

    @abstractmethod
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        """物理演算前の更新"""
        pass

    @abstractmethod
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        """物理演算後の更新"""
        pass


class Missile(SpecialWeapon):
    """ミサイル（誘導弾）スペシャル発射制御クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        owner: Tank,
        team_type: TeamType,
        setting: MissileSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__owner = owner
        self.__team_type = team_type
        self.__setting = setting
        self.__fire_interval = setting.fire_interval
        self.__bullet_list: list[MissileBullet] = []
        self.__timer = 0.0
        self.__bullet_index = 0
        self.__num_missiles = 0

        self.__shuwa_shuwa_graphics: Optional[ShuwaShuwaGraphics] = None

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__idle)
        self.__mode = WeaponMode.READY

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    def __get_target(self) -> Tank | None:
        return self.__owner.get_enemy_tank()

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_finished]
        if self.__shuwa_shuwa_graphics:
            self.__shuwa_shuwa_graphics.update(current_raw_time)

    def __idle(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__shuwa_shuwa_graphics = None
        if self.__mode is WeaponMode.READY and self.__owner.status.sp >= 1.0:
            self.__state_machine.set_next_state(self.__appear)

    def __appear(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__owner.apply_use_special()
            self.__launch_pos = self.__owner.get_pos() + Point3(0, 0, 10)
            self.__shuwa_shuwa_graphics = ShuwaShuwaGraphics(self.__base, self.__team_type, self.__launch_pos, ctx.current_raw_time)
        appear_time = 1.0
        if appear_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__fire)

    def __fire(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__num_missiles = 3

        target = self.__get_target()
        if target is None:
            return
        if target.status.hp <= 0:
            return

        self.__timer += ctx.dt
        if self.__timer >= self.__fire_interval:
            bullet = MissileBullet(
                self.__base,
                self.__battle,
                self.__owner,
                self.__bullet_index,
                self.__team_type,
                self.__setting,
                self.__launch_pos,
                target,
            )
            self.__bullet_list.append(bullet)
            self.__bullet_index += 1
            self.__timer -= self.__fire_interval
            self.__num_missiles -= 1

        if self.__num_missiles <= 0:
            self.__state_machine.set_next_state(self.__idle)


class Rain(SpecialWeapon):
    """雨ふらし（インク雲）スペシャル発射制御クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        owner: Tank,
        team_type: TeamType,
        setting: RainSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__owner = owner
        self.__team_type = team_type
        self.__setting = setting
        self.__bullet_list: list[RainBullet] = []
        self.__bullet_index = 0

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__idle)

        self.__owner_pos: Point3 = Point3(0, 0, 0)
        self.__owner_direction: Vec3 = Vec3(1, 0, 0)
        self.__mode = WeaponMode.READY

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_finished]

    def __idle(self, ctx: StateContext) -> None:
        if self.__mode is WeaponMode.READY and self.__owner.status.sp >= 1.0:
            self.__state_machine.set_next_state(self.__appear)

    def __appear(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__owner.apply_use_special()
            self.__owner_pos = self.__owner.get_pos()
            self.__owner_direction = self.__owner.get_direction()
            self.__updraft_graphics = RainUpdraftGraphics(
                self.__base, self.__team_type, self.__owner_pos
            )
        self.__updraft_graphics.update(ctx.state_time)
        appear_time = 1.0
        if appear_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__fire)

    def __fire(self, ctx: StateContext) -> None:
        if ctx.is_first:
            bullet = RainBullet(
                self.__base,
                self.__battle,
                self.__owner,
                self.__bullet_index,
                self.__team_type,
                self.__setting,
                self.__owner_pos,
                self.__owner_direction,
            )
            self.__bullet_list.append(bullet)
            self.__bullet_index += 1
        self.__state_machine.set_next_state(self.__idle)


class ElectromagneticWave(SpecialWeapon):
    """電磁波（EMP）スペシャル発射制御クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        owner: Tank,
        team_type: TeamType,
        setting: ElectromagneticWaveSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__owner = owner
        self.__team_type = team_type
        self.__setting = setting
        self.__bullet_list: list[ElectromagneticWaveBullet] = []
        self.__bullet_index = 0

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__idle)

        self.__owner_pos: Point3 = Point3(0, 0, 0)
        self.__owner_direction: Vec3 = Vec3(1, 0, 0)

        self.__mode = WeaponMode.READY

        self.__shuwa_shuwa_graphics: Optional[ShuwaShuwaGraphics] = None

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_finished]
        if self.__shuwa_shuwa_graphics:
            self.__shuwa_shuwa_graphics.update(current_raw_time)

    def __idle(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__shuwa_shuwa_graphics = None
        if self.__mode is WeaponMode.READY and self.__owner.status.sp >= 1.0:
            self.__state_machine.set_next_state(self.__appear)

    def __appear(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__owner.apply_use_special()
            self.__owner_pos = self.__owner.get_pos()
            self.__owner_direction = self.__owner.get_direction()
            self.__shuwa_shuwa_graphics = ShuwaShuwaGraphics(self.__base, self.__team_type, self.__owner_pos, ctx.current_raw_time)
        appear_time = 1.0
        if appear_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__fire)

    def __fire(self, ctx: StateContext) -> None:
        if ctx.is_first:
            bullet = ElectromagneticWaveBullet(
                self.__base,
                self.__battle,
                self.__owner,
                self.__bullet_index,
                self.__team_type,
                self.__setting,
                self.__owner_pos,
                self.__owner_direction,
            )
            self.__bullet_list.append(bullet)
            self.__bullet_index += 1
        self.__state_machine.set_next_state(self.__idle)


class HyperBeam(SpecialWeapon):
    """ハイパービームスペシャル発射制御クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        owner: Tank,
        team_type: TeamType,
        setting: HyperBeamSetting,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__owner = owner
        self.__team_type = team_type
        self.__setting = setting
        self.__bullet_list: list[HyperBeamBullet] = []
        self.__bullet_index = 0

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__idle)

        self.__launch_pos: Point3 = Point3(0, 0, 0)
        self.__owner_direction: Vec3 = Vec3(1, 0, 0)
        self.__mode = WeaponMode.READY

        self.__shuwa_shuwa_graphics: Optional[ShuwaShuwaGraphics] = None

    @override
    def set_mode(self, weapon_mode: WeaponMode) -> None:
        self.__mode = weapon_mode

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        for bullet in self.__bullet_list:
            bullet.pre_physics_update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        for bullet in self.__bullet_list:
            bullet.post_physics_update(current_raw_time, dt)
        self.__bullet_list = [b for b in self.__bullet_list if not b.is_finished]
        if self.__shuwa_shuwa_graphics:
            self.__shuwa_shuwa_graphics.update(current_raw_time)

    def __idle(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__shuwa_shuwa_graphics = None
        if self.__mode is WeaponMode.READY and self.__owner.status.sp >= 1.0:
            self.__state_machine.set_next_state(self.__appear)

    def __appear(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__owner.apply_use_special()
            self.__launch_pos = self.__owner.get_pos() + Point3(0, 0, self.__setting.radius)
            self.__owner_direction = self.__owner.get_direction()
            self.__shuwa_shuwa_graphics = ShuwaShuwaGraphics(self.__base, self.__team_type, self.__launch_pos, ctx.current_raw_time)
        appear_time = 1.0
        if appear_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__pre_fire)

    def __pre_fire(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__pre_bullet_graphics = HyperBeamBulletPreGraphics(
                self.__base,
                self.__team_type,
                self.__launch_pos,
                self.__owner_direction,
                self.__setting.radius,
                self.__setting.bullet_range,
            )
        self.__pre_bullet_graphics.update(ctx.state_frame, ctx.state_time)
        pre_fire_duration = 1.0
        if pre_fire_duration <= ctx.state_time:
            self.__pre_bullet_graphics.delete()
            self.__state_machine.set_next_state(self.__fire)

    def __fire(self, ctx: StateContext) -> None:
        if ctx.is_first:
            bullet = HyperBeamBullet(
                self.__base,
                self.__battle,
                self.__owner,
                self.__bullet_index,
                self.__team_type,
                self.__setting,
                self.__launch_pos,
                self.__owner_direction,
            )
            self.__bullet_list.append(bullet)
            self.__bullet_index += 1

        if self.__setting.duration <= ctx.state_time:
            self.__state_machine.set_next_state(self.__idle)