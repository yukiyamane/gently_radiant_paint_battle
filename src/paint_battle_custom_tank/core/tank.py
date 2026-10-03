"""戦車の物理演算・状態管理・武器統括モジュール。"""

from __future__ import annotations
from enum import Enum, auto
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.bullet import BulletRigidBodyNode, BulletSphereShape, BulletWorld
# pyrefly: ignore [missing-import]
from panda3d.core import BitMask32, Point3, TransformState, VBase3, Vec3

from paint_battle_custom_tank.core.battle_event_data import DamageEvent, PaintEvent
from paint_battle_custom_tank.core.tank_status import TankCondition, TankStatus
from paint_battle_custom_tank.core.collision_data import CollisionGroup
from paint_battle_custom_tank.core.main_weapon import WeaponFactory
from paint_battle_custom_tank.core.paint import BrushType
from paint_battle_custom_tank.core.setting import (
    SpecialWeaponType,
    TeamType,
    WeaponType,
    tank_setting,
)
from paint_battle_custom_tank.core.special_weapon import SpecialWeaponFactory
from paint_battle_custom_tank.core.weapon import WeaponMode
from paint_battle_custom_tank.graphics.tank import (
    TankDeathExplosionGraphics,
    TankGraphics,
    SpecialActivationUI,
    
)
from paint_battle_custom_tank.shared.util.randomizer import battle_randomizer
from paint_battle_custom_tank.shared.util.yamane_state_machine import (
    StateContext,
    StateMachine,
)

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.main import MyApp


class TankPhysics:
    """戦車のBullet剛体物理挙動（移動・旋回P制御・速度制限・オフセット計算）を管理するクラス。"""

    def __init__(
        self,
        base: MyApp,
        physics_world: BulletWorld,
        owner: Tank,
        team_type: TeamType,
    ) -> None:
        node = BulletRigidBodyNode("tank")
        radius = 10.0
        sphere_shape = BulletSphereShape(radius)
        node.addShape(sphere_shape)
        node.setMass(20.0)
        node.setRestitution(1.0)

        shape_right = BulletSphereShape(3.0)
        ts_r = TransformState.makePos(Vec3(-13, 0, 0))
        node.addShape(shape_right, ts_r)

        shape_left = BulletSphereShape(3.0)
        ts_l = TransformState.makePos(Vec3(13, 0, 0))
        node.addShape(shape_left, ts_l)

        node.setLinearFactor(Vec3(1, 1, 0))
        node.setAngularFactor(Vec3(0, 0, 0))

        self.__team_type = team_type

        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_TANK,
            TeamType.BRAVO: CollisionGroup.BRAVO_TANK,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        node.setPythonTag("collision_group", registry[team_type])
        node.setPythonTag("owner", owner)

        physics_world.attachRigidBody(node)
        self.__node: BulletRigidBodyNode = node

    def look_at_enemy(self, enemy_pos: Vec3, dt: float) -> None:
        """比例制御（P制御）を用いて敵の方向へ向く角速度を更新する。"""
        current_pos = self.get_pos()
        current_hpr = self.get_hpr()
        current_h = current_hpr[0]

        direction = enemy_pos - current_pos
        direction.z = 0

        if direction.length_squared() > 0.001:
            target_h = math.degrees(math.atan2(direction.x, -direction.y))
            angle_diff = (target_h - current_h + 180.0) % 360.0 - 180.0

            if abs(angle_diff) < 0.5:
                self.__node.setAngularVelocity(Vec3(0, 0, 0))
                return

            p_gain = 12.0
            angular_velocity_z = math.radians(angle_diff) * p_gain
            max_turn_speed = math.radians(180.0)
            angular_velocity_z = max(
                min(angular_velocity_z, max_turn_speed), -max_turn_speed
            )
            self.__node.setAngularVelocity(Vec3(0, 0, angular_velocity_z))

    def limit_speed(self) -> None:
        """戦車の最高移動速度を制限する。"""
        max_speed = 50.0
        vel = self.__node.getLinearVelocity()
        speed = vel.length()
        if speed > max_speed:
            self.__node.setLinearVelocity(vel.normalized() * max_speed)

    def apply_gravity_to_center(self, center_pos: Vec3 = Vec3(0, 0, 0), strength: float = 200.0) -> None:
        """
        ステージ中央へ引き寄せる中心力を加える。
        壁で止まったり、場外に停滞するのを防ぐ。
        """
        current_pos = self.get_pos()
        to_center = center_pos - current_pos
        to_center.z = 0  # 2D平面上の移動（XY軸のみ）

        distance = to_center.length()
        if distance > 0.1: # 中央に完全に重なっていない場合のみ適用
            # 1. 引力の方向単位ベクトル
            dir_to_center = to_center.normalized()
            # パターンA: 距離に関わらず一定の力で引く（シンプルで安定）
            force_vector = dir_to_center * strength
            # パターンB: 中心から離れるほど強く引っ張る場合（必要に応じて切り替え）
            # force_vector = dir_to_center * (strength * (distance / 50.0))
            # 剛体の中心に力を加える（毎フレーム呼ぶことで加速・吸いつきが発生）
            self.__node.applyCentralForce(force_vector)

    def apply_impulse(self, vector: Vec3) -> None:
        self.__node.applyImpulse(vector, Vec3(0, 0, 0))

    def set_pos_hpr(self, pos: Vec3, hpr: VBase3) -> None:
        """戦車の位置・回転を強制設定し、物理キャッシュをリセットする。"""
        self.__node.setTransformDirty()
        ts = TransformState.makePosHpr(pos, hpr)
        self.__node.setTransform(ts)
        if self.__team_type is TeamType.ALPHA:
            self.__node.setLinearVelocity(Vec3(20, 0, 0))
        else:
            self.__node.setLinearVelocity(Vec3(-20, 0, 0))
        self.__node.setAngularVelocity(Vec3(0, 0, 0))
        self.__node.setActive(True)

    def get_pos(self) -> Point3:
        return self.__node.getTransform().getPos()

    def get_hpr(self) -> VBase3:
        return self.__node.getTransform().getHpr()

    def get_sub_left_pos(self) -> Vec3:
        tank_pos = self.__node.getTransform().getPos()
        tank_quat = self.__node.getTransform().getQuat()
        local_offset = Vec3(13, 0, 0)
        rotated_offset = tank_quat.xform(local_offset)
        return tank_pos + rotated_offset

    def get_sub_right_pos(self) -> Vec3:
        tank_pos = self.__node.getTransform().getPos()
        tank_quat = self.__node.getTransform().getQuat()
        local_offset = Vec3(-13, 0, 0)
        rotated_offset = tank_quat.xform(local_offset)
        return tank_pos + rotated_offset

    def get_direction(self) -> Vec3:
        forward = self.__node.getTransform().getQuat().getForward()
        forward *= -1
        return forward


class Tank:
    """戦車本体のロジック・武装・ステートを統合するクラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        team_type: TeamType,
        main_weapon_type: WeaponType,
        sub_weapon_type: WeaponType,
        special_weapon_type: SpecialWeaponType,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__team_type = team_type

        self.__main_weapon = WeaponFactory.create_main(
            main_weapon_type, base, battle, self, team_type
        )
        self.__sub_weapon_left = WeaponFactory.create_sub(
            sub_weapon_type, base, battle, self, team_type
        )
        self.__sub_weapon_right = WeaponFactory.create_sub(
            sub_weapon_type, base, battle, self, team_type
        )
        self.__special_weapon = SpecialWeaponFactory.create(
            special_weapon_type, base, battle, self, team_type
        )

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__move)

        if team_type is TeamType.ALPHA:
            self.__initial_pos = Point3(-180, 0, 0)
            self.__initial_hpr = VBase3(90, 0, 0)
        elif team_type is TeamType.BRAVO:
            self.__initial_pos = Point3(180, 0, 0)
            self.__initial_hpr = VBase3(-90, 0, 0)
        else:
            raise ValueError(f"Invalid team_type: {team_type}")

        self.__physics = TankPhysics(
            self.__base, self.__battle.physics_world, self, team_type
        )
        self.__physics.set_pos_hpr(self.__initial_pos, self.__initial_hpr)
        self.__status = TankStatus()

        self.__graphics = TankGraphics(
            self.__base,
            self.__team_type,
            main_weapon_type,
            sub_weapon_type,
            sub_weapon_type,
        )
        self.__graphics.set_pos(self.__physics.get_pos())
        self.__graphics.set_hpr(self.__physics.get_hpr())

    @property
    def status(self) -> TankStatus:
        return self.__status

    @property
    def team_type(self) -> TeamType:
        return self.__team_type

    def apply_damage(self, event: DamageEvent) -> None:
        """ダメージを適用し、HPが0になった場合は撃破処理およびリスポーン遷移を行う。"""
        if self.__status.condition is TankCondition.DEAD:
            return
        if self.__status.condition is TankCondition.INVINCIBLE:
            return
        self.__status.hp -= event.amount
        if self.__status.hp <= 0:
            self.__status.hp = 0
            self.__status.condition = TankCondition.DEAD
            TankDeathPaint(
                self.__base,
                self.__battle,
                event.attacker,
                event.attacker_team,
                self.__physics.get_pos(),
            )
            TankDeathExplosionGraphics(
                self.__base, event.attacker_team, self.__physics.get_pos()
            )
            self.__status.death_count += 1
            event.attacker.status.kill_count += 1

            self.__state_machine.set_next_state(self.__respawn_wait)

    def apply_use_special(self) -> None:
        """スペシャル発動によるSP消費。"""
        self.__status.sp -= 1.0
        self.__status.special_count += 1
        SpecialActivationUI(self.__base, self.__team_type, self.__physics.get_pos())

    def apply_impulse(self, vector: Vec3) -> None:
        self.__physics.apply_impulse(vector)

    def apply_repaint_area(self, area: float) -> None:
        """塗布面積に応じたスペシャルゲージ（SP）チャージ処理。"""
        max_sp_area = 20000.0
        self.__status.sp += area / max_sp_area
        if self.__status.sp > self.__status.max_sp:
            self.__status.sp = self.__status.max_sp
        self.__status.area_painted += area

    def disable_input(self) -> None:
        self.__main_weapon.set_mode(WeaponMode.SUPPRESSED)
        self.__sub_weapon_left.set_mode(WeaponMode.SUPPRESSED)
        self.__sub_weapon_right.set_mode(WeaponMode.SUPPRESSED)
        self.__special_weapon.set_mode(WeaponMode.SUPPRESSED)
        self.__status.condition = TankCondition.INVINCIBLE

    def get_pos(self) -> Point3:
        return self.__physics.get_pos()

    def get_hpr(self) -> VBase3:
        return self.__physics.get_hpr()

    def get_direction(self) -> Vec3:
        return self.__physics.get_direction()

    def get_enemy_tank(self) -> Optional[Tank]:
        """敵対チームの戦車インスタンスを取得する。"""
        for team_type, team in self.__battle.team_dict.items():
            if team_type is self.__team_type:
                continue
            return team.tank_list[0]
        return None

    def __face_target(self, dt: float) -> None:
        enemy = self.get_enemy_tank()
        if enemy is None or enemy.status.hp <= 0:
            return
        self.__physics.look_at_enemy(enemy.get_pos(), dt)

    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        self.__main_weapon.pre_physics_update(
            current_raw_time,
            dt,
            self.__physics.get_pos(),
            self.__physics.get_direction(),
        )
        self.__sub_weapon_left.pre_physics_update(
            current_raw_time,
            dt,
            self.__physics.get_sub_left_pos(),
            self.__physics.get_direction(),
        )
        self.__sub_weapon_right.pre_physics_update(
            current_raw_time,
            dt,
            self.__physics.get_sub_right_pos(),
            self.__physics.get_direction(),
        )
        self.__special_weapon.pre_physics_update(current_raw_time, dt)

    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__graphics.set_pos(self.__physics.get_pos())
        self.__graphics.set_hpr(self.__physics.get_hpr())
        self.__main_weapon.post_physics_update(current_raw_time, dt)
        self.__sub_weapon_left.post_physics_update(current_raw_time, dt)
        self.__sub_weapon_right.post_physics_update(current_raw_time, dt)
        self.__special_weapon.post_physics_update(current_raw_time, dt)

    def __move(self, ctx: StateContext) -> None:
        self.__face_target(ctx.dt)
        self.__physics.apply_gravity_to_center()
        self.__physics.limit_speed()


    def __respawn_wait(self, ctx: StateContext) -> None:
        #バトル終了時はリスポーンしないように
        if self.__status.condition is TankCondition.INVINCIBLE:
            return

        if ctx.is_first:
            self.__status.condition = TankCondition.DEAD
            self.__main_weapon.set_mode(WeaponMode.SUPPRESSED)
            self.__sub_weapon_left.set_mode(WeaponMode.SUPPRESSED)
            self.__sub_weapon_right.set_mode(WeaponMode.SUPPRESSED)
            self.__special_weapon.set_mode(WeaponMode.SUPPRESSED)
            self.__physics.set_pos_hpr(Point3(0, 0, -30), VBase3(0, 0, 0))

        self.__status.time_since_death = ctx.state_time

        if tank_setting.respawn_time <= self.__status.time_since_death:
            self.__state_machine.set_next_state(self.__respawn)

    def __respawn(self, ctx: StateContext) -> None:
        #バトル終了時はリスポーンしないように
        if self.__status.condition is TankCondition.INVINCIBLE:
            return

        if ctx.is_first:
            self.__status.hp = self.__status.max_hp
            self.__status.time_since_death = 0.0
            self.__status.condition = TankCondition.ALIVE
            self.__main_weapon.set_mode(WeaponMode.READY)
            self.__sub_weapon_left.set_mode(WeaponMode.READY)
            self.__sub_weapon_right.set_mode(WeaponMode.READY)
            self.__special_weapon.set_mode(WeaponMode.READY)
            self.__physics.set_pos_hpr(self.__initial_pos, self.__initial_hpr)
            self.__state_machine.set_next_state(self.__move)



class TankDeathPaint:
    """戦車撃破時の大円ペイントおよび放射状飛沫ペイント処理クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        attacker: Tank,
        attacker_team_type: TeamType,
        pos: Point3,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__attacker = attacker
        self.__attacker_team_type = attacker_team_type
        self.__pos = pos
        self.__splash_time = 0.05
        self.__paint_death_main()
        self.__task_name = f"tank_death_paint_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        if task.time >= self.__splash_time:
            self.__paint_death_splash()
            return Task.done
        return Task.cont

    def __paint_death_main(self) -> None:
        event = PaintEvent(
            self.__attacker,
            BrushType.BIG_NOISED_CIRCLE,
            self.__pos,
            20.0,
            Vec3(1, 0, 0),
            self.__attacker_team_type,
        )
        self.__battle.stage.paint_stage.request_paint(event)

    def __paint_death_splash(self) -> None:
        num_splash = 8
        degree_per_splash = 360.0 / num_splash
        center_pos = self.__pos
        radius = 30.0
        for i in range(num_splash):
            degree = degree_per_splash * i + battle_randomizer.randint(
                0, round(degree_per_splash // 2)
            )
            direction = Vec3(
                math.cos(math.radians(degree)), math.sin(math.radians(degree)), 0
            )
            pos = center_pos + direction * radius
            event = PaintEvent(
                self.__attacker,
                BrushType.STRETCHED,
                pos,
                5.0,
                direction,
                self.__attacker_team_type,
            )
            self.__battle.stage.paint_stage.request_paint(event)