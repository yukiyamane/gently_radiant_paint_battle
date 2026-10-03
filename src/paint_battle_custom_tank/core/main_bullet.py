"""メインおよびサブ武器用弾丸の物理挙動・判定制御モジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, override
from abc import ABC, abstractmethod
import math
# pyrefly: ignore [missing-import]
from panda3d.bullet import (
    BulletGhostNode,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
)
# pyrefly: ignore [missing-import]
from panda3d.core import BitMask32, NodePath, Point3, TransformState, Vec3

from paint_battle_custom_tank.core.battle_event_data import DamageEvent, PaintEvent
from paint_battle_custom_tank.core.collision_data import CollisionGroup
from paint_battle_custom_tank.core.main_weapon_setting import (
    BounceSetting,
    ExplodingSetting,
    LaserSetting,
    SplashSetting,
    ThreeWaySetting,
)
from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.core.tank_status import TankCondition
from paint_battle_custom_tank.graphics.bullet import BulletDamageText
from paint_battle_custom_tank.graphics.main_bullet import (
    BounceBulletGraphics,
    BounceBulletHitGraphics,
    ExplodingBulletGraphics,
    ExplodingExplosionGraphics,
    LaserBulletGraphics,
    LaserBulletHitGraphics,
    ThreeWayBulletGraphics,
    ThreeWayBulletHitGraphics,
)
from paint_battle_custom_tank.shared.util.randomizer import battle_randomizer
from paint_battle_custom_tank.shared.util.yamane_state_machine import (
    StateContext,
    StateMachine,
)

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import Tank
    from paint_battle_custom_tank.core.special_bullet import ElectromagneticWaveBullet
    from paint_battle_custom_tank.main import MyApp


class BulletPaintController:
    """弾丸移動中および着弾時のインク塗布要求を管理するコントローラ。"""

    def __init__(
        self,
        battle: Battle,
        tank_ref: Tank,
        team_type: TeamType,
        splash_setting: SplashSetting,
    ) -> None:
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = splash_setting
        self.__prev_pos: Optional[Vec3] = None
        self.__accumulated_distance: float = (
            splash_setting.mid_distance * battle_randomizer.random()
        )

    def update_mid(self, pos: Vec3, velocity: Vec3) -> None:
        """弾丸の現在位置から中間インク飛沫の発生判定を行う。"""
        if self.__prev_pos is None:
            self.__prev_pos = pos
            return

        segment = pos - self.__prev_pos
        segment_length = segment.length()
        direction = segment.normalized()
        interval = self.__setting.mid_distance
        dist = interval - self.__accumulated_distance

        while dist <= segment_length:
            splash_pos = self.__prev_pos + direction * dist
            self.__paint_mid(splash_pos, velocity)
            dist += interval

        self.__accumulated_distance = segment_length - (dist - interval)
        self.__prev_pos = pos

    def __paint_mid(self, pos: Vec3, velocity: Vec3) -> None:
        event = PaintEvent(
            self.__tank_ref,
            self.__setting.mid_brush_type,
            pos,
            self.__setting.mid_radius,
            velocity.normalized(),
            self.__team_type,
        )
        self.__battle.stage.paint_stage.request_paint(event)

    def paint_impact(self, pos: Vec3, velocity: Vec3) -> None:
        """弾丸着弾時の大サイズインク塗布を要求する。"""
        event = PaintEvent(
            self.__tank_ref,
            self.__setting.impact_brush_type,
            pos,
            self.__setting.impact_radius,
            velocity.normalized(),
            self.__team_type,
        )
        self.__battle.stage.paint_stage.request_paint(event)


class Bullet(ABC):
    """弾丸の基底クラス。"""

    @abstractmethod
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        pass

    @abstractmethod
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        pass


class BounceBullet(Bullet):
    """壁で跳ね返るバウンス弾クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: BounceSetting,
        tank_pos: Vec3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__index = index
        self.__battle = battle
        self.__tank_ref = tank_ref

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__move)

        self.__team_type = team_type
        self.__setting = setting
        self.__damage = setting.damage
        self.__life_time = setting.bullet_range / setting.bullet_speed
        self.__max_bounce = setting.max_bounce
        self.__bounce_count = 0
        self.__is_dead = False

        self.__paint = BulletPaintController(
            battle, self.__tank_ref, team_type, setting.splash_setting
        )
        self.__physics = BounceBulletPhysics(
            battle.physics_world, self, setting, team_type, tank_pos, direction
        )
        self.__graphics: Optional[BounceBulletGraphics] = BounceBulletGraphics(
            base, self.__team_type, setting.radius
        )
        self.__already_hit_target_set: set[Tank] = set()

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        """他オブジェクトとの衝突時処理。"""
        if self.__is_dead:
            return

        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")

        if collision_group in (CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_EMP):
            self.__state_machine.set_next_state(self.__dead)
            return
            
        self.__bounce_count += 1
        if self.__bounce_count > self.__max_bounce:
            self.__state_machine.set_next_state(self.__dead)
        else:
            event = PaintEvent(
                self.__tank_ref,
                self.__setting.splash_setting.mid_brush_type,
                self.__physics.get_pos(),
                self.__setting.splash_setting.mid_radius,
                self.__physics.get_linear_velocity().normalized(),
                self.__team_type,
            )
            self.__battle.stage.paint_stage.request_paint(event)

        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):  
            owner: Tank
            if owner.team_type is self.__team_type:
                return
            if owner.status.condition is TankCondition.DEAD:
                return                    
            if owner in self.__already_hit_target_set:
                return
            self.__already_hit_target_set.add(owner)
            damage_event = DamageEvent(
                self.__tank_ref, self.__setting.damage, self.__team_type
            )
            owner.apply_damage(damage_event)
            BounceBulletHitGraphics(
                self.__base,
                self.__team_type,
                self.__physics.get_pos(),
                self.__setting.radius,
            )
            BulletDamageText(
                self.__base,
                self.__team_type,
                self.__setting.damage,
                self.__physics.get_pos(),
            )
            self.__state_machine.set_next_state(self.__dead)

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:        
        self.__state_machine.update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics is not None:
            self.__graphics.update(self.__physics.get_pos())

    def __move(self, ctx: StateContext) -> None:
        self.__paint.update_mid(self.__physics.get_pos(), self.__physics.get_linear_velocity())
        if self.__life_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__dead)

    def __dead(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__paint.paint_impact(
                self.__physics.get_pos(), self.__physics.get_linear_velocity()
            )
            self.__physics.delete()
            if self.__graphics is not None:
                self.__graphics.delete()
                self.__graphics = None
            self.__is_dead = True

    @property
    def is_dead(self) -> bool:
        return self.__is_dead


class BounceBulletPhysics:
    """バウンス弾のBullet剛体物理制御クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: BounceBullet,
        setting: BounceSetting,
        team_type: TeamType,
        tank_pos: Vec3,
        direction: Vec3,
    ) -> None:
        node = BulletRigidBodyNode("bounce_bullet")
        radius = setting.radius
        shape = BulletSphereShape(radius)
        node.addShape(shape)
        node.setRestitution(1.0)
        node.setMass(1.0)
        node.setLinearFactor(Vec3(1, 1, 0))
        node.setAngularFactor(Vec3(0, 0, 1))

        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        physics_world.attachRigidBody(node)
        node.setPythonTag("on_contact", owner.on_contact)
        node.setPythonTag("owner", owner)
        node.setPythonTag("collision_group", registry[team_type])

        pos = tank_pos + direction * setting.battery_radius
        node.setTransform(TransformState.makePos(pos))
        node.setLinearVelocity(direction * setting.bullet_speed)
        node.notifyCollisions(True)

        self.__physics_world = physics_world
        self.__node = node

    def get_pos(self) -> Point3:
        return self.__node.getTransform().getPos()

    def get_linear_velocity(self) -> Vec3:
        return self.__node.getLinearVelocity()

    def delete(self) -> None:
        self.__physics_world.removeRigidBody(self.__node)


class ExplodingBullet(Bullet):
    """着弾時に爆風判定を発生させる爆発弾クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: ExplodingSetting,
        tank_pos: Vec3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__move)
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__index = index
        self.__team_type = team_type
        self.__direct_damage = setting.direct_damage
        self.__life_time = setting.bullet_range / setting.bullet_speed
        self.__explosion_damage = setting.explosion_damage
        self.__explosion_radius = setting.explosion_radius
        self.__setting = setting
        self.__is_exploded = False
        self.__is_dead = False

        self.__direct_hit_target_set: set[Tank] = set()
        self.__explosion_hit_target_set: set[Tank] = set()

        self.__physics: Optional[ExplodingBulletPhysics] = ExplodingBulletPhysics(
            battle.physics_world, self, setting, team_type, tank_pos, direction
        )
        self.__paint = BulletPaintController(
            battle, self.__tank_ref, team_type, setting.splash_setting
        )
        self.__graphics: Optional[ExplodingBulletGraphics] = ExplodingBulletGraphics(
            base, self.__team_type, setting.radius
        )
        self.__explosion_physics: Optional[ExplodingExplosionPhysics] = None

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_dead:
            return
        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")

        if collision_group in (CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_EMP):
            self.__state_machine.set_next_state(self.__dead)
            return

        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            if owner.team_type is self.__team_type:
                return
            if owner not in self.__direct_hit_target_set:
                self.__direct_hit_target_set.add(owner)

        if self.__is_exploded:
            return
        self.__state_machine.set_next_state(self.__explode)

    def on_contact_explosion(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_dead:
            return
        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")
        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            if owner.team_type is self.__team_type:
                return
            if owner not in self.__explosion_hit_target_set:
                self.__explosion_hit_target_set.add(owner)
                damage_event = DamageEvent(
                    self.__tank_ref,
                    self.__setting.explosion_damage,
                    self.__team_type,
                )
                owner.apply_damage(damage_event)
                BulletDamageText(
                    self.__base,
                    self.__team_type,
                    self.__setting.explosion_damage,
                    self.__explosion_pos,
                    )

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics and self.__physics:
            self.__graphics.set_pos(self.__physics.get_pos())

    def __move(self, ctx: StateContext) -> None:
        if self.__physics is None:
            raise RuntimeError("physics is None")
        pos = self.__physics.get_pos()
        self.__paint.update_mid(pos, self.__physics.get_linear_velocity())
        if self.__life_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__explode)

    def __explode(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__physics is None:
                raise RuntimeError("physics is None")
            self.__paint.paint_impact(
                self.__physics.get_pos(), self.__physics.get_linear_velocity()
            )
            self.__explosion_physics = ExplodingExplosionPhysics(
                self.__battle.physics_world,
                self,
                self.__setting,
                self.__team_type,
                self.__physics.get_pos(),
            )
            self.__explosion_pos = self.__explosion_physics.get_pos()
            ExplodingExplosionGraphics(
                self.__base,
                self.__team_type,
                self.__setting.explosion_radius,
                self.__explosion_pos,
            )

            self.__physics.delete()
            self.__physics = None
            if self.__graphics:
                self.__graphics.delete()
                self.__graphics = None
            self.__is_exploded = True
        else:
            if self.__explosion_physics:
                self.__explosion_physics.delete()
            self.__state_machine.set_next_state(self.__dead)

    def __dead(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__physics: #empでデスした場合、念のため削除
                self.__physics.delete()
                self.__physics = None
            if self.__graphics:
                self.__graphics.delete()
                self.__graphics = None
            self.__is_dead = True

    @property
    def is_dead(self) -> bool:
        return self.__is_dead


class ExplodingBulletPhysics:
    """爆発弾のBullet剛体物理制御クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: ExplodingBullet,
        setting: ExplodingSetting,
        team_type: TeamType,
        tank_pos: Point3,
        direction: Vec3,
    ) -> None:
        node = BulletRigidBodyNode("exploding_bullet")
        radius = setting.radius
        shape = BulletSphereShape(radius)
        node.addShape(shape)
        node.setRestitution(1.0)
        node.setMass(1.0)
        node.setLinearFactor(Vec3(1, 1, 0))
        node.setAngularFactor(Vec3(0, 0, 1))

        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        physics_world.attachRigidBody(node)

        pos = tank_pos + direction * setting.battery_radius
        node.setTransform(TransformState.makePos(pos))
        node.setLinearVelocity(direction * setting.bullet_speed)
        node.setPythonTag("on_contact", owner.on_contact)
        node.setPythonTag("owner", owner)
        node.setPythonTag("collision_group", registry[team_type])
        node.notifyCollisions(True)

        self.__node: Optional[BulletRigidBodyNode] = node
        self.__physics_world = physics_world

    def get_pos(self) -> Point3:
        if self.__node is None:
            return Point3(0, 0, 0)
        return self.__node.getTransform().getPos()

    def get_linear_velocity(self) -> Vec3:
        if self.__node is None:
            return Vec3(0, 0, 0)
        return self.__node.getLinearVelocity()

    def delete(self) -> None:
        if self.__node is not None:
            self.__physics_world.removeRigidBody(self.__node)
            self.__node = None


class ExplodingExplosionPhysics:
    """爆発時のゴーストノードによる範囲ダメージ判定クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: ExplodingBullet,
        setting: ExplodingSetting,
        team_type: TeamType,
        pos: Point3,
    ) -> None:
        ghost = BulletGhostNode("explosion")
        ghost_shape = BulletSphereShape(setting.explosion_radius)
        ghost.addShape(ghost_shape)
        ghost.setTransform(TransformState.makePos(pos))
        ghost.setPythonTag("on_contact", owner.on_contact_explosion)

        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        ghost.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        ghost.notifyCollisions(True)
        physics_world.attachGhost(ghost)

        self.__node: Optional[BulletGhostNode] = ghost
        self.__physics_world = physics_world

    def get_pos(self) -> Point3:
        if self.__node is None:
            return Point3(0, 0, 0)
        return self.__node.getTransform().getPos()

    def delete(self) -> None:
        if self.__node is not None:
            self.__physics_world.removeGhost(self.__node)
            self.__node = None


class ThreeWayBullet(Bullet):
    """3方向拡散弾クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: ThreeWaySetting,
        pos: Vec3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__index = index
        self.__battle = battle
        self.__tank_ref = tank_ref

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__move)

        self.__team_type = team_type
        self.__setting = setting
        self.__damage = setting.damage
        self.__life_time = setting.bullet_range / setting.bullet_speed
        self.__is_dead = False

        self.__paint = BulletPaintController(
            battle, self.__tank_ref, team_type, setting.splash_setting
        )
        self.__physics: Optional[ThreeWayBulletPhysics] = ThreeWayBulletPhysics(
            battle.physics_world, self, setting, team_type, pos, direction
        )
        self.__graphics: Optional[ThreeWayBulletGraphics] = ThreeWayBulletGraphics(
            base, self.__team_type, setting.radius
        )
        self.__already_hit_target_set: set[Tank] = set()

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_dead:
            return

        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")

        if collision_group in (CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_EMP):
            self.__state_machine.set_next_state(self.__dead)
            return

        if self.__physics:
            event = PaintEvent(
                self.__tank_ref,
                self.__setting.splash_setting.mid_brush_type,
                self.__physics.get_pos(),
                self.__setting.splash_setting.mid_radius,
                self.__physics.get_linear_velocity().normalized(),
                self.__team_type,
            )
            self.__battle.stage.paint_stage.request_paint(event)
        self.__state_machine.set_next_state(self.__dead)

        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            if owner.team_type != self.__team_type:
                if owner in self.__already_hit_target_set:
                    return
                self.__already_hit_target_set.add(owner)
                damage_event = DamageEvent(
                    self.__tank_ref, self.__setting.damage, self.__team_type
                )
                owner.apply_damage(damage_event)
                if self.__physics:
                    ThreeWayBulletHitGraphics(
                        self.__base,
                        self.__team_type,
                        self.__physics.get_pos(),
                        self.__setting.radius,
                    )
                if self.__physics:
                    BulletDamageText(
                        self.__base,
                        self.__team_type,
                        self.__setting.damage,
                        self.__physics.get_pos(),
                    )
                self.__state_machine.set_next_state(self.__dead)

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics and self.__physics:
            self.__graphics.set_pos(self.__physics.get_pos())

    def __move(self, ctx: StateContext) -> None:
        if self.__physics:
            self.__paint.update_mid(self.__physics.get_pos(), self.__physics.get_linear_velocity())
        if self.__life_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__dead)

    def __dead(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__physics:
                self.__paint.paint_impact(
                    self.__physics.get_pos(), self.__physics.get_linear_velocity()
                )
            if self.__physics:
                self.__physics.delete()
                self.__physics = None
            if self.__graphics:
                self.__graphics.delete()
                self.__graphics = None
            self.__is_dead = True

    @property
    def is_dead(self) -> bool:
        return self.__is_dead


class ThreeWayBulletPhysics:
    """3方向弾のBullet剛体物理制御クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: ThreeWayBullet,
        setting: ThreeWaySetting,
        team_type: TeamType,
        pos: Vec3,
        direction: Vec3,
    ) -> None:
        node = BulletRigidBodyNode("three_way_bullet")
        radius = setting.radius
        shape = BulletSphereShape(radius)
        node.addShape(shape)
        node.setRestitution(1.0)
        node.setMass(1.0)
        node.setLinearFactor(Vec3(1, 1, 0))
        node.setAngularFactor(Vec3(0, 0, 1))

        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        physics_world.attachRigidBody(node)
        node.setPythonTag("on_contact", owner.on_contact)
        node.setPythonTag("owner", owner)
        node.setPythonTag("collision_group", registry[team_type])

        node.setTransform(TransformState.makePos(pos))
        node.setLinearVelocity(direction * setting.bullet_speed)
        #node.notifyCollisions(True)

        self.__physics_world = physics_world
        self.__node = node

    def get_pos(self) -> Point3:
        return self.__node.getTransform().getPos()

    def get_linear_velocity(self) -> Vec3:
        return self.__node.getLinearVelocity()

    def delete(self) -> None:
        self.__physics_world.removeRigidBody(self.__node)


class LaserBullet(Bullet):
    """高速貫通判定を行うレーザー光線弾クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: LaserSetting,
        tank_pos: Vec3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__index = index
        self.__battle = battle
        self.__tank_ref = tank_ref

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__move)

        self.__team_type = team_type
        self.__setting = setting
        self.__damage = setting.damage
        self.__life_time = setting.bullet_range / setting.bullet_speed
        self.__is_dead = False

        self.__paint = BulletPaintController(
            battle, self.__tank_ref, team_type, setting.splash_setting
        )
        self.__physics = LaserBulletPhysics(
            battle.physics_world, self, setting, team_type, tank_pos, direction
        )
        self.__graphics = LaserBulletGraphics(
            base,
            self.__team_type,
            setting.radius,
            self.__physics.get_pos(),
            self.__physics.get_hpr(),
        )
        self.__already_hit_target_set: set[Tank] = set()

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_dead:
            return

        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")

        event = PaintEvent(
            self.__tank_ref,
            self.__setting.splash_setting.mid_brush_type,
            self.__physics.get_pos(),
            self.__setting.splash_setting.mid_radius,
            self.__physics.get_linear_velocity().normalized(),
            self.__team_type,
        )
        self.__battle.stage.paint_stage.request_paint(event)
        self.__state_machine.set_next_state(self.__dead)

        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            owner: Tank
            if owner.team_type is self.__team_type:
                return
            if owner in self.__already_hit_target_set:
                return
            self.__already_hit_target_set.add(owner)
            damage_event = DamageEvent(
                self.__tank_ref, self.__setting.damage, self.__team_type
            )
            owner.apply_damage(damage_event)
            vec = owner.get_pos() - self.__physics.get_pos()
            vec = vec.normalized()
            owner.apply_impulse(vec * self.__setting.knockback)
            LaserBulletHitGraphics(
                self.__base,
                self.__team_type,
                self.__physics.get_pos(),
                self.__setting.radius,
            )
            BulletDamageText(
                self.__base,
                self.__team_type,
                self.__setting.damage,
                self.__physics.get_pos(),
            )
            self.__state_machine.set_next_state(self.__dead)

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics and self.__physics:
            pass
            #self.__graphics.set_pos(self.__physics.get_pos())
            #self.__graphics.set_hpr(self.__physics.get_hpr())

    def __move(self, ctx: StateContext) -> None:
        if ctx.is_first:
            pos = self.__physics.get_pos()
            vel = self.__physics.get_linear_velocity()
            self.__paint.update_mid(pos, vel)

        self.__physics.update(ctx.dt)

        pos = self.__physics.get_pos()
        vel = self.__physics.get_linear_velocity()
        length = self.__physics.get_length()

        self.__paint.update_mid(pos, vel)
        self.__graphics.update(length)

        if self.__life_time <= ctx.state_time:
            self.__state_machine.set_next_state(self.__dead)

    def __dead(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__paint.paint_impact(
                self.__physics.get_pos(), self.__physics.get_linear_velocity()
            )
            self.__physics.delete()
        else:
            self.__graphics.delete()
            self.__is_dead = True

    @property
    def is_dead(self) -> bool:
        return self.__is_dead


class LaserBulletPhysics:
    """スイープテストによるレーザー光線の物理走査クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: LaserBullet,
        setting: LaserSetting,
        team_type: TeamType,
        pos: Vec3,
        direction: Vec3,
    ) -> None:
        self.__world = physics_world
        self.__owner = owner
        self.__setting = setting
        self.__team_type = team_type

        self.__pos = pos
        self.__direction = direction
        self.__speed = setting.bullet_speed
        self.__radius = setting.radius

        self.__current_length = 0.1
        self.__is_hit = False
        self.__hit_pos: Optional[Vec3] = None
        self.__shape = BulletSphereShape(self.__radius)

        self.__mask = BitMask32.allOff()
        self.__mask.setBit(CollisionGroup.WALL)

        if self.__team_type == TeamType.ALPHA:
            self.__mask.setBit(CollisionGroup.BRAVO_TANK)
            self.__mask.setBit(CollisionGroup.BRAVO_EMP)
        else:
            self.__mask.setBit(CollisionGroup.ALPHA_TANK)
            self.__mask.setBit(CollisionGroup.ALPHA_EMP)


    def update(self, dt: float) -> None:
        if self.__is_hit:
            return

        move = self.__direction * self.__speed * dt
        next_pos = self.__pos + move

        # 1. スイープテストを実行
        from_transform = TransformState.makePos(self.__pos)
        to_transform = TransformState.makePos(next_pos)
        result = self.__world.sweep_test_closest(
            self.__shape, from_transform, to_transform, self.__mask
        )

        if result.has_hit():
            hit_node = result.getNode()
            # --- A. EMP
            if self.__is_emp_node(hit_node):
                emp: ElectromagneticWaveBullet = hit_node.getPythonTag("owner")
                pre_distance_from_emp_center = (self.__pos - emp.get_pos()).length()
                if pre_distance_from_emp_center < emp.get_current_radius():
                    self.__is_hit = True
                    if isinstance(hit_node, BulletRigidBodyNode):
                        self.__owner.on_contact(hit_node)
                    return
            # --- B. 通常の剛体オブジェクト（壁・戦車など） ---
            self.__is_hit = True
            hit_pos = result.get_hit_pos()
            hit_distance = (hit_pos - self.__pos).length()
            self.__advance_position(hit_pos, hit_distance)
            if isinstance(hit_node, BulletRigidBodyNode):
                self.__owner.on_contact(hit_node)
        else:
            # 何にも当たらなかった場合の通常移動
            self.__advance_position(next_pos, move.length())


    # ------------------------------------------------------------------
    #  超高速弾対応：線分と球の正確な交差判定（数学解法）
    # ------------------------------------------------------------------

    def __check_shell_cross(self, start_pos: Point3, end_pos: Point3, emp: ElectromagneticWaveBullet):
        """
        線分 (start_pos -> end_pos) が EMP 球体 (中心: emp_pos, 半径: R) と交差するか判定し、
        最初に着弾（交差）する座標を返す。
        """
        emp_pos = emp.get_pos()
        R = emp.get_current_radius()

        # 始点と終点の中心からの距離
        d_start = (start_pos - emp_pos).length()
        d_end = (end_pos - emp_pos).length()

        # パターン1: 内側から発射・移動して外へ抜け出そうとした場合
        if d_start < R and d_end >= R:
            t = (R - d_start) / (d_end - d_start) if d_end != d_start else 0.0
            hit_pos = start_pos + (end_pos - start_pos) * t
            return True, hit_pos

        # パターン2: 超高速で外側からEMPを貫通（飛び越し）した場合、または外から突入した場合
        # 線分: P(t) = start + t * V (0 <= t <= 1)
        V = end_pos - start_pos
        L = start_pos - emp_pos

        # 2次方程式 a*t^2 + b*t + c = 0 の係数
        a = V.dot(V)
        if a == 0:
            return False, None

        b = 2.0 * L.dot(V)
        c = L.dot(L) - R * R

        discriminant = b * b - 4 * a * c  # 判別式

        # 判別式 < 0 なら球と直線は交差しない
        if discriminant < 0:
            return False, None

        # 交点 t の解を計算（小さい方の t が手前の交点）
        sqrt_disc = math.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2.0 * a)
        t2 = (-b + sqrt_disc) / (2.0 * a)

        # 線分上 (0 <= t <= 1) に交点があるか確認
        for t in (t1, t2):
            if 0.0 <= t <= 1.0:
                hit_pos = start_pos + V * t
                return True, hit_pos

        return False, None

    # ------------------------------------------------------------------
    #  可読性とメンテナンス性を高めるためのヘルパーメソッド
    # ------------------------------------------------------------------

    def __advance_position(self, new_pos: Point3, distance_delta: float) -> None:
        """弾の位置と総移動距離を更新する"""
        self.__pos = new_pos
        self.__current_length += distance_delta

    def __is_emp_node(self, node: BulletRigidBodyNode) -> bool:
        """衝突したノードがEMPかどうかを判定"""
        group = node.getPythonTag("collision_group")
        return group in (CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_EMP)

    def __is_hitting_emp_shell(self, hit_pos: Point3, emp: ElectromagneticWaveBullet) -> bool:
        """
        衝突位置(hit_pos)が、EMPの「外枠（広がりつつある膜の厚み内）」にあるかを判定する。
        """
        distance = (hit_pos - emp.get_pos()).length()
        
        # 前フレームの半径（内縁）〜 現在の半径（外縁）
        prev_r = emp.get_prev_radius()
        curr_r = emp.get_current_radius()
        
        # 高速なレーザーが通過する際のスルー防止用マージン
        margin = 0.2

        # 衝突位置が「前フレームの半径」と「現フレームの半径」の間にあれば「外枠にヒット」
        is_shell = (prev_r - margin) <= distance <= (curr_r + margin)
        return is_shell

    def get_pos(self) -> Vec3:
        return self.__pos

    def get_hpr(self) -> Vec3:
        tmp = NodePath("tmp")
        tmp.lookAt(self.__direction, Vec3(0, 0, 1))
        hpr = tmp.getHpr()
        hpr.setX(hpr.x + 90)
        return hpr

    def get_linear_velocity(self) -> Vec3:
        return self.__direction * self.__speed

    def get_length(self) -> float:
        return self.__current_length

    def delete(self) -> None:
        pass