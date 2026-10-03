"""スペシャル武器用弾丸および広域エフェクトの物理挙動・判定制御モジュール。"""

from __future__ import annotations
import math
from typing import TYPE_CHECKING, Optional, Set, override
from abc import ABC, abstractmethod
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.bullet import (
    BulletCapsuleShape,
    BulletCylinderShape,
    BulletGhostNode,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
)
# pyrefly: ignore [missing-import]
from panda3d.core import BitMask32, NodePath, Point3, TransformState, Vec3

from paint_battle_custom_tank.core.battle_event_data import DamageEvent, PaintEvent
from paint_battle_custom_tank.core.collision_data import CollisionGroup
from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.core.special_weapon_setting import (
    ElectromagneticWaveSetting,
    HyperBeamSetting,
    MissileSetting,
    RainSetting,
)
from paint_battle_custom_tank.core.tank_status import TankCondition
from paint_battle_custom_tank.graphics.bullet import BulletDamageText
from paint_battle_custom_tank.graphics.special_bullet import (
    ElectromagneticWaveBulletGraphics,
    HyperBeamBulletGraphics,
    MissileBulletGraphics,
    MissileExplosionGraphics,
    MissileImpactMarkerGraphics,
    RainBulletGraphics,
    RainDropBulletGraphics,
)
from paint_battle_custom_tank.shared.util.randomizer import battle_randomizer
from paint_battle_custom_tank.shared.util.yamane_prepare import globalClock
from paint_battle_custom_tank.shared.util.yamane_state_machine import (
    StateContext,
    StateMachine,
)

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import Tank
    from paint_battle_custom_tank.main import MyApp



class SpecialBullet(ABC):
    """スペシャル武器用弾丸の抽象基底クラス"""

    @abstractmethod
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        pass

    @abstractmethod
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        pass
    
    


class MissileBullet(SpecialBullet):
    """放物線を描いて敵頭上から落下・着弾爆発するミサイル誘導弾クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: MissileSetting,
        initial_pos: Point3,
        target: Tank,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__ascend)
        self.__team_type = team_type
        self.__setting = setting
        self.__index = index
        self.__is_finished = False
        self.__target = target

        self.__duration = 5.0
        self.__remaining_time = self.__duration
        self.__gravity = 98.0

        self.__explosion_hit_target_set: set[Tank] = set()
        self.__physics: Optional[MissileBulletPhysics] = MissileBulletPhysics(
            battle.physics_world, self, setting, team_type, initial_pos
        )
        self.__graphics: Optional[MissileBulletGraphics] = MissileBulletGraphics(base, team_type)
        self.__velocity: Vec3 = Vec3(0, 0, 0)
        self.__explosion_physics: Optional[MissileExplosionPhysics] = None
        self.__impact_marker_graphics: Optional[MissileImpactMarkerGraphics] = None

    @property
    def is_finished(self) -> bool:
        return self.__is_finished

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        pass

    def on_contact_explosion(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_finished:
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

    def __paint_splash(self) -> None:
        num_splash = self.__setting.num_splash
        degree_per_splash = 360.0 / num_splash
        center_pos = self.__explosion_pos
        distance = self.__setting.splash_paint_distance
        brush_type = self.__setting.splash_brush_type
        paint_radius = self.__setting.splash_paint_radius
        for i in range(num_splash):
            degree = degree_per_splash * i + battle_randomizer.randint(
                0, round(degree_per_splash // 2)
            )
            direction = Vec3(
                math.cos(math.radians(degree)), math.sin(math.radians(degree)), 0
            )
            pos = center_pos + direction * distance
            event = PaintEvent(
                self.__tank_ref,
                brush_type,
                pos,
                paint_radius,
                direction,
                self.__team_type,
            )
            self.__battle.stage.paint_stage.request_paint(event)

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics and self.__physics:
            self.__graphics.update(self.__physics.get_pos(), self.__velocity)

    def __ascend(self, ctx: StateContext) -> None:
        if self.__physics is None:
            return
        bullet_pos = self.__physics.get_pos()
        target_pos = self.__target.get_pos()

        dx = target_pos.x - bullet_pos.x
        dy = target_pos.y - bullet_pos.y
        dz = target_pos.z - bullet_pos.z

        self.__remaining_time = max(self.__remaining_time - ctx.dt, 0.01)

        vx = dx / self.__remaining_time
        vy = dy / self.__remaining_time
        vz = (
            dz + 0.5 * self.__gravity * (self.__remaining_time**2)
        ) / self.__remaining_time

        self.__velocity = Vec3(vx, vy, vz)
        new_bullet_pos = bullet_pos + self.__velocity * ctx.dt
        self.__physics.set_pos(new_bullet_pos)

        if vz < 0:
            self.__state_machine.set_next_state(self.__descend)

    def __descend(self, ctx: StateContext) -> None:
        if ctx.is_first:
            target_pos = self.__target.get_pos()
            impact_pos = Point3(target_pos.x, target_pos.y, 0.0)
            self.__impact_marker_graphics = MissileImpactMarkerGraphics(
                self.__base, self.__team_type, impact_pos
            )
        
        # 重力による速度変化
        self.__velocity.z -= self.__gravity * ctx.dt
        
        # 移動前の位置を保持
        if self.__physics is None:
            return
        old_bullet_pos = self.__physics.get_pos()
        
        # 移動後の位置を計算
        new_bullet_pos = old_bullet_pos + self.__velocity * ctx.dt

        # --- ★【修正点】z=0 への着弾位置補正ロジック ---
        if new_bullet_pos.z <= 0:
            # 1フレーム前の位置(z>0)とめり込んだ位置(z<=0)の差分
            dz = old_bullet_pos.z - new_bullet_pos.z
            
            # ゼロ除算防止（ありえないケースだが安全のため）
            if dz == 0:
                final_impact_pos = Point3(new_bullet_pos.x, new_bullet_pos.y, 0.0)
            else:
                # old_bullet_pos.z から z=0 に達するまでの時間の割合 (0.0 ~ 1.0)
                t = old_bullet_pos.z / dz
                
                # X, Y もその割合で補間し、z=0 の正確な位置を算出
                hit_x = old_bullet_pos.x + (new_bullet_pos.x - old_bullet_pos.x) * t
                hit_y = old_bullet_pos.y + (new_bullet_pos.y - old_bullet_pos.y) * t
                final_impact_pos = Point3(hit_x, hit_y, 0.0)

            # 物理と見た目を完全に z=0 の位置に合わせる
            self.__physics.set_pos(final_impact_pos)
            
            # 爆発ステートへ
            self.__state_machine.set_next_state(self.__explode)
            return # このフレームの処理は終了
        # -----------------------------------------------
        # まだ空中にある場合は、そのまま更新
        self.__physics.set_pos(new_bullet_pos)

    def __explode(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__physics is None:
                return
            event = PaintEvent(
                self.__tank_ref,
                self.__setting.brush_type,
                self.__physics.get_pos(),
                self.__setting.paint_radius,
                Vec3(0, 0, 1),
                self.__team_type,
            )
            self.__battle.stage.paint_stage.request_paint(event)
            self.__explosion_physics = MissileExplosionPhysics(
                self.__battle.physics_world,
                self,
                self.__setting,
                self.__team_type,
                self.__physics.get_pos(),
            )
            self.__explosion_pos = self.__explosion_physics.get_pos()
            MissileExplosionGraphics(
                self.__base,
                self.__team_type,
                self.__setting.explosion_radius,
                self.__explosion_pos,
            )
            if self.__impact_marker_graphics:
                self.__impact_marker_graphics.delete()
            self.__physics.delete()
            self.__physics = None
            if self.__graphics:
                self.__graphics.delete()
                self.__graphics = None

        else:
            self.__paint_splash()
            self.__state_machine.set_next_state(self.__dead)

    def __dead(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__explosion_physics:
                self.__explosion_physics.delete()
                self.__explosion_physics = None
            self.__is_finished = True


class MissileBulletPhysics:
    """ミサイルのゴーストノード物理管理クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: MissileBullet,
        setting: MissileSetting,
        team_type: TeamType,
        initial_pos: Point3,
    ) -> None:
        node = BulletGhostNode("missile_bullet")
        radius = setting.radius
        shape = BulletSphereShape(radius)
        node.addShape(shape)
        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        node.setKinematic(True)
        physics_world.attachGhost(node)
        node.setPythonTag("on_contact", owner.on_contact)
        node.notifyCollisions(True)
        node.setTransform(TransformState.makePos(initial_pos))

        self.__physics_world = physics_world
        self.__node: Optional[BulletGhostNode] = node

    def set_pos(self, pos: Vec3) -> None:
        if self.__node:
            self.__node.setTransform(TransformState.makePos(pos))

    def get_pos(self) -> Point3:
        if self.__node is None:
            return Point3(0, 0, 0)
        return self.__node.getTransform().getPos()

    def delete(self) -> None:
        if self.__node:
            self.__physics_world.removeGhost(self.__node)
            self.__node = None


class MissileExplosionPhysics:
    """ミサイル着弾爆発のゴーストノード物理管理クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: MissileBullet,
        setting: MissileSetting,
        team_type: TeamType,
        pos: Vec3,
    ) -> None:
        node = BulletGhostNode("missile_explosion")
        radius = setting.explosion_radius
        shape = BulletSphereShape(radius)
        node.addShape(shape)
        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        node.setKinematic(True)
        physics_world.attachGhost(node)
        node.setPythonTag("on_contact", owner.on_contact_explosion)
        node.notifyCollisions(True)
        node.setTransform(TransformState.makePos(pos))

        self.__physics_world = physics_world
        self.__node: Optional[BulletGhostNode] = node
        #print(self.get_pos())

    def get_pos(self) -> Point3:
        if self.__node is None:
            return Point3(0, 0, 0)
        return self.__node.getTransform().getPos()

    def delete(self) -> None:
        if self.__node:
            self.__physics_world.removeGhost(self.__node)
            self.__node = None


class RainBullet(SpecialBullet):
    """インクの雨雲を前進させ広範囲に雨を降らせる雨ふらしクラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: RainSetting,
        initial_pos: Point3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__move)
        self.__team_type = team_type
        self.__setting = setting
        self.__index = index
        self.__is_finished = False

        self.__direction = direction
        self.__damage_timer_dict: dict[Tank, float] = {}
        self.__contacted_target_set_this_frame: set[Tank] = set()

        self.__physics: Optional[RainBulletPhysics] = RainBulletPhysics(
            battle.physics_world, self, setting, team_type, initial_pos
        )
        self.__graphics: Optional[RainBulletGraphics] = RainBulletGraphics(
            base, battle.physics_world, team_type, setting.radius
        )
        self.__drop_accumulator = 0.0

    @property
    def is_finished(self) -> bool:
        return self.__is_finished

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_finished:
            return
        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")
        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            if owner.team_type != self.__team_type:
                if owner in self.__contacted_target_set_this_frame:
                    return
                self.__contacted_target_set_this_frame.add(owner)
                dt = globalClock.getDt()
                if owner not in self.__damage_timer_dict:
                    self.__damage_timer_dict[owner] = 0.0
                self.__damage_timer_dict[owner] += dt
                if self.__damage_timer_dict[owner] >= self.__setting.damage_interval:
                    damage_event = DamageEvent(
                        self.__tank_ref,
                        self.__setting.damage_per_interval,
                        self.__team_type,
                    )
                    owner.apply_damage(damage_event)
                    BulletDamageText(
                        self.__base,
                        self.__team_type,
                        self.__setting.damage_per_interval,
                        owner.get_pos(),
                    )
                    self.__damage_timer_dict[owner] -= self.__setting.damage_interval

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        self.__contacted_target_set_this_frame.clear()

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics and self.__physics:
            self.__graphics.update(self.__physics.get_pos())

    def __move(self, ctx: StateContext) -> None:
        speed = self.__setting.move_speed
        if self.__physics is None:
            raise RuntimeError("RainBulletPhysics is None")
        pos = self.__physics.get_pos()
        new_pos = pos + self.__direction * speed * ctx.dt
        self.__physics.set_pos(new_pos)

        self.__drop_accumulator += self.__setting.number_of_drop_per_second * ctx.dt
        num_drops = int(self.__drop_accumulator)
        self.__drop_accumulator -= num_drops

        for _ in range(num_drops):
            angle = battle_randomizer.uniform(0, 2 * math.pi)
            r = self.__setting.radius * math.sqrt(battle_randomizer.random())
            x = new_pos.x + r * math.cos(angle)
            y = new_pos.y + r * math.sin(angle)
            drop_pos = Point3(x, y, 100)
            RainDropBullet(
                self.__base,
                self.__battle,
                self.__tank_ref,
                self.__team_type,
                self.__setting,
                drop_pos,
            )

        if self.__setting.duration <= ctx.state_time:
            if self.__graphics:
                self.__graphics.delete()
                self.__graphics = None
            if self.__physics:
                self.__physics.delete()
                self.__physics = None
            self.__state_machine.set_next_state(self.__finish)

    def __finish(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__is_finished = True


class RainBulletPhysics:
    """雨ふらしのシリンダー型ゴーストノード物理管理クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: RainBullet,
        setting: RainSetting,
        team_type: TeamType,
        initial_pos: Point3,
    ) -> None:
        node = BulletGhostNode("rain_bullet")
        radius = setting.radius
        shape = BulletCylinderShape(radius, 100.0, 2)
        node.addShape(shape)
        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        node.setIntoCollideMask(BitMask32.bit(registry[team_type]))
        node.setKinematic(True)
        physics_world.attachGhost(node)
        node.setPythonTag("on_contact", owner.on_contact)
        node.notifyCollisions(True)
        node.setTransform(TransformState.makePos(initial_pos))

        self.__physics_world = physics_world
        self.__node: Optional[BulletGhostNode] = node

    def set_pos(self, pos: Point3) -> None:
        if self.__node:
            self.__node.setTransform(TransformState.makePos(pos))

    def get_pos(self) -> Point3:
        if self.__node is None:
            return Point3(0, 0, 0)
        return self.__node.getTransform().getPos()

    def delete(self) -> None:
        if self.__node:
            self.__physics_world.removeGhost(self.__node)
            self.__node = None


class RainDropBullet:
    """雨ふらしから落下する個々のインク滴クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        team_type: TeamType,
        setting: RainSetting,
        initial_pos: Point3,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = setting

        self.__pos = initial_pos
        self.__velocity = Vec3(0, 0, -200)
        self.__graphics = RainDropBulletGraphics(base, team_type)
        self.__task_name = f"rain_drop_bullet_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __paint(self) -> None:
        event = PaintEvent(
            self.__tank_ref,
            self.__setting.brush_type,
            self.__pos,
            self.__setting.paint_radius,
            Vec3(0, 0, 1),
            self.__team_type,
        )
        self.__battle.stage.paint_stage.request_paint(event)

    def __update(self, task: Task.Task) -> int:
        dt = globalClock.getDt()
        self.__pos += self.__velocity * dt
        self.__graphics.set_pos(self.__pos)
        if self.__pos.z <= 0:
            self.__paint()
            self.__graphics.impact()
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__graphics.delete()


class ElectromagneticWaveBullet(SpecialBullet):
    """全方位へ波紋状に拡大し敵弾を消滅・敵戦車にダメージを与える電磁波クラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        owner: Tank,
        index: int,
        team_type: TeamType,
        setting: ElectromagneticWaveSetting,
        initial_pos: Point3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__owner = owner
        self.__team_type = team_type
        self.__setting = setting
        self.__index = index
        self.__is_finished = False

        self.__direction = direction
        self.__pos = initial_pos
        self.__already_hit_set = set()

        self.__graphics: Optional[ElectromagneticWaveBulletGraphics] = ElectromagneticWaveBulletGraphics(
            base, team_type, initial_pos
        )
        self.__physics: Optional[ElectromagneticWaveBulletPhysics] = ElectromagneticWaveBulletPhysics(
            battle.physics_world, self, setting, team_type, initial_pos
        )

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__expanding_state)

    @property
    def is_finished(self) -> bool:
        return self.__is_finished

    def get_pos(self) -> Point3:
        return self.__pos

    def get_current_radius(self) -> float:
        if self.__physics is None:
            raise RuntimeError("ElectromagneticWaveBulletPhysics is None")
        return self.__physics.get_current_radius()

    def get_prev_radius(self) -> float:
        if self.__physics is None:
            raise RuntimeError("ElectromagneticWaveBulletPhysics is None")
        return self.__physics.get_prev_radius()

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_finished:
            return

        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")

        node_pos = other_node.getTransform().getPos()

        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            owner: Tank
            if owner.team_type is self.__team_type:
                return
            if owner in self.__already_hit_set:
                return
            self.__already_hit_set.add(owner)
            damage_event = DamageEvent(
                self.__owner, self.__setting.damage, self.__team_type
            )
            if owner.status.condition is TankCondition.ALIVE:
                BulletDamageText(
                    self.__base,
                    self.__team_type,
                    self.__setting.damage,
                    node_pos,
                )
            owner.apply_damage(damage_event)

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics and self.__physics:
            self.__graphics.update(self.__physics.get_current_radius())

    def __expanding_state(self, ctx: StateContext) -> None:
        if self.__physics is None:
            raise RuntimeError("ElectromagneticWaveBulletPhysics is None")
        self.__physics.update_expansion(ctx.dt)
        current_radius = self.__physics.get_current_radius()
        if current_radius >= self.__setting.max_radius:
            self.__state_machine.set_next_state(self.__dead)

    def __dead(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__physics is None:
                raise RuntimeError("ElectromagneticWaveBulletPhysics is None")
            if self.__graphics is None:
                raise RuntimeError("ElectromagneticWaveBulletGraphics is None")
            self.__physics.delete()
            self.__physics = None
            self.__graphics.delete()
            self.__graphics = None
            self.__is_finished = True


class ElectromagneticWaveBulletPhysics:
    """電磁波の拡大球体ゴーストノード物理管理クラス。"""

    def __init__(
        self,
        physics_world: BulletWorld,
        owner: ElectromagneticWaveBullet,
        setting: ElectromagneticWaveSetting,
        team_type: TeamType,
        initial_pos: Point3,
    ) -> None:
        self.__world = physics_world
        self.__owner = owner
        self.__setting = setting
        self.__team_type = team_type
        self.__pos = initial_pos

        self.__prev_radius = 0.01
        self.__current_radius = 0.01
        self.__max_radius = setting.max_radius
        self.__expand_speed = setting.expand_speed

        self.__ghost = BulletGhostNode("EMP_Wave_Ghost")
        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_EMP,
            TeamType.BRAVO: CollisionGroup.BRAVO_EMP,
        }
        mask = BitMask32.bit(registry[team_type])
        self.__ghost.setIntoCollideMask(mask)
        self.__ghost.setPythonTag("on_contact", owner.on_contact)
        self.__ghost.setPythonTag("owner", owner)
        self.__ghost.setPythonTag("collision_group", registry[team_type])
        self.__ghost.notifyCollisions(True)

        self.__shape: Optional[BulletSphereShape] = None
        self.__update_ghost_shape(self.__current_radius)
        self.__ghost.setTransform(TransformState.makePos(self.__pos))
        self.__world.attachGhost(self.__ghost)

    def __update_ghost_shape(self, radius: float) -> None:
        if self.__shape is not None:
            self.__ghost.removeShape(self.__shape)
        self.__shape = BulletSphereShape(radius)
        self.__ghost.addShape(self.__shape)

    def set_pos(self, pos: Point3) -> None:
        self.__pos = pos
        self.__ghost.setTransform(TransformState.makePos(self.__pos))

    def update_expansion(self, dt: float) -> None:
        self.__prev_radius = self.__current_radius
        self.__current_radius += self.__expand_speed * dt
        if self.__current_radius > self.__max_radius:
            self.__current_radius = self.__max_radius
        self.__update_ghost_shape(self.__current_radius)

    def get_current_radius(self) -> float:
        return self.__current_radius

    def get_prev_radius(self) -> float:
        return self.__prev_radius

    def delete(self) -> None:
        if self.__ghost is not None:
            self.__world.removeGhost(self.__ghost)
            self.__ghost = None


class HyperBeamBullet(SpecialBullet):
    """巨大な円筒状の破壊ビームを照射し続けるハイパービームクラス。"""

    def __init__(
        self,
        base: MyApp,
        battle: Battle,
        tank_ref: Tank,
        index: int,
        team_type: TeamType,
        setting: HyperBeamSetting,
        initial_pos: Point3,
        direction: Vec3,
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__tank_ref = tank_ref
        self.__team_type = team_type
        self.__setting = setting
        self.__index = index
        self.__is_finished = False

        self.__initial_pos = initial_pos
        self.__direction = direction
        self.__damage_timer_dict: dict[Tank, float] = {}
        self.__contacted_target_set_this_frame: set[Tank] = set()

        self.__physics: Optional[HyperBeamBulletPhysics] = HyperBeamBulletPhysics(
            base,
            battle.physics_world,
            self,
            setting,
            team_type,
            initial_pos,
            self.__direction,
        )
        self.__graphics: Optional[HyperBeamBulletGraphics] = HyperBeamBulletGraphics(
            base,
            team_type,
            initial_pos,
            self.__direction,
            setting.radius,
            setting.bullet_range,
        )
        self.__drop_accumulator = 0.0
        self.__u_axis, self.__v_axis = self.__calculate_perpendicular_axes(
            self.__direction
        )

        self.__state_machine: StateMachine = StateMachine(self)
        self.__state_machine.set_next_state(self.__beam)

    def __calculate_perpendicular_axes(
        self, direction: Vec3
    ) -> tuple[Vec3, Vec3]:
        if abs(direction.z) < 0.99:
            temp_vec = Vec3(0, 0, 1)
        else:
            temp_vec = Vec3(1, 0, 0)
        u = direction.cross(temp_vec).normalized()
        v = direction.cross(u).normalized()
        return u, v

    @property
    def is_finished(self) -> bool:
        return self.__is_finished

    def on_contact(self, other_node: BulletRigidBodyNode) -> None:
        if self.__is_finished:
            return
        collision_group = other_node.getPythonTag("collision_group")
        owner = other_node.getPythonTag("owner")
        if (
            collision_group in (CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK)
            and owner is not None
        ):
            owner: Tank
            if owner.team_type is self.__team_type:
                return
            if owner.status.condition is TankCondition.DEAD:
                return                    
            if owner in self.__contacted_target_set_this_frame:
                return
            self.__contacted_target_set_this_frame.add(owner)
            dt = globalClock.getDt()
            if owner not in self.__damage_timer_dict:
                self.__damage_timer_dict[owner] = 0.0
            self.__damage_timer_dict[owner] += dt
            if self.__damage_timer_dict[owner] >= self.__setting.damage_interval:
                damage_event = DamageEvent(
                    self.__tank_ref,
                    self.__setting.damage_per_interval,
                    self.__team_type,
                )
                owner.apply_damage(damage_event)
                BulletDamageText(
                    self.__base,
                    self.__team_type,
                    self.__setting.damage_per_interval,
                    owner.get_pos(),
                )
                self.__damage_timer_dict[owner] -= self.__setting.damage_interval

    @override
    def pre_physics_update(self, current_raw_time: float, dt: float) -> None:
        self.__state_machine.update(current_raw_time, dt)
        self.__contacted_target_set_this_frame.clear()

    @override
    def post_physics_update(self, current_raw_time: float, dt: float) -> None:
        if self.__graphics:
            self.__graphics.update(current_raw_time, dt)

    def __beam(self, ctx: StateContext) -> None:
        self.__drop_accumulator += self.__setting.number_of_drop_per_second * ctx.dt
        num_drops = int(self.__drop_accumulator)
        self.__drop_accumulator -= num_drops

        for _ in range(num_drops):
            line_dist = battle_randomizer.uniform(0, self.__setting.bullet_range)
            center_on_beam = self.__initial_pos + (self.__direction * line_dist)
            angle = battle_randomizer.uniform(0, 2 * math.pi)
            r = (self.__setting.radius) * math.sqrt(battle_randomizer.random())
            offset = (self.__u_axis * (r * math.cos(angle))) + (
                self.__v_axis * (r * math.sin(angle))
            )
            spawn_pos = center_on_beam + offset

            event = PaintEvent(
                self.__tank_ref,
                self.__setting.brush_type,
                spawn_pos,
                self.__setting.paint_radius,
                Vec3(0, 0, 1),
                self.__team_type,
            )
            self.__battle.stage.paint_stage.request_paint(event)

        if self.__setting.duration <= ctx.state_time:
            self.__state_machine.set_next_state(self.__finish)

    def __finish(self, ctx: StateContext) -> None:
        if ctx.is_first:
            if self.__physics is None:
                raise RuntimeError("HyperBeamBulletPhysics is None")
            if self.__graphics is None:
                raise RuntimeError("HyperBeamBulletGraphics is None")
            self.__physics.delete()
            self.__physics = None
            self.__graphics.delete()
            self.__graphics = None
            self.__is_finished = True


class HyperBeamBulletPhysics:
    """ハイパービームのカプセル型ゴーストノード物理管理クラス。"""

    def __init__(
        self,
        base: MyApp,
        physics_world: BulletWorld,
        owner: HyperBeamBullet,
        setting: HyperBeamSetting,
        team_type: TeamType,
        pos: Point3,
        direction: Vec3,
    ) -> None:
        self.__physics_world = physics_world
        self.__owner = owner
        dir_norm = direction.normalized()

        node = BulletGhostNode("hyper_beam_bullet")
        radius = setting.radius
        bullet_range = setting.bullet_range
        shape = BulletCapsuleShape(radius, bullet_range, 1)
        node.addShape(shape)

        registry = {
            TeamType.ALPHA: CollisionGroup.ALPHA_BULLET,
            TeamType.BRAVO: CollisionGroup.BRAVO_BULLET,
        }
        mask = BitMask32.bit(registry[team_type])
        node.setIntoCollideMask(mask)
        physics_world.attachGhost(node)

        node.setPythonTag("on_contact", owner.on_contact)
        node.setPythonTag("owner", owner)
        node.setPythonTag("collision_group", registry[team_type])
        node.notifyCollisions(True)

        self.__np = NodePath(node)
        center_pos = pos + (dir_norm * (bullet_range * 0.5))
        self.__np.setPos(center_pos)
        self.__np.lookAt(center_pos + dir_norm)
        self.__np.reparentTo(base.render)
        node.setTransform(self.__np.getTransform())

        self.__node: Optional[BulletGhostNode] = node
        self.__direction = dir_norm

    def get_pos(self) -> Point3:
        if self.__node is None:
            return Point3(0, 0, 0)
        return self.__node.getTransform().getPos()

    def get_hpr(self) -> Vec3:
        tmp = NodePath("tmp")
        tmp.lookAt(self.__direction, Vec3(0, 0, 1))
        hpr = tmp.getHpr()
        hpr.setX(hpr.x + 90)
        return hpr

    def get_linear_velocity(self) -> Vec3:
        if self.__node is None:
            return Vec3(0, 0, 0)
        return self.__node.getLinearVelocity()

    def delete(self) -> None:
        if self.__node:
            self.__physics_world.removeGhost(self.__node)
            self.__node = None
        if self.__np:
            self.__np.removeNode()
