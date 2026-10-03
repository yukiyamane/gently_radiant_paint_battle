"""スペシャル武器用弾丸・広域エフェクトの3D描画モジュール。"""

from __future__ import annotations
import math
from typing import TYPE_CHECKING
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.bullet import BulletWorld
# pyrefly: ignore [missing-import]
from panda3d.core import (
    LineSegs,
    Material,
    NodePath,
    Point3,
    TransparencyAttrib,
    VBase3,
    Vec3,
    Vec4,
)

from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.core.collision_data import CollisionGroup
from paint_battle_custom_tank.graphics.setting import graphics_setting
from paint_battle_custom_tank.shared.util.randomizer import fx_randomizer
from paint_battle_custom_tank.shared.util.yamane_prepare import globalClock

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp



class ShuwaShuwaGraphics:
    def __init__(self, base: MyApp, team_type: TeamType, pos: Point3, start_time: float) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__pos = pos
        self.__generated_count: int = 0
        self.__per_second = 16.0
        self.__start_time = start_time

    def update(self, current_raw_time: float) -> None:
        target_count = int((current_raw_time - self.__start_time) * self.__per_second)
        spawn_count = target_count - self.__generated_count
        for _ in range(spawn_count):
            ParticleShuwaShuwaGraphics(self.__base, self.__team_type, self.__pos)
        self.__generated_count = target_count

class ParticleShuwaShuwaGraphics:
    def __init__(self, base: MyApp, team_type: TeamType, pos: Vec3) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m.copyTo(base.render)
        )
        self.__node_path.setScale(2)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        self.__node_path.setAlphaScale(1)

        pos_offset = Vec3(fx_randomizer.uniform(-3.0, 3.0), fx_randomizer.uniform(-3.0, 3.0), fx_randomizer.uniform(-3.0, 3.0))
        self.__node_path.setPos(pos + pos_offset)
        
        x = fx_randomizer.uniform(-50, 50)
        y = fx_randomizer.uniform(-50, 50)
        z = fx_randomizer.uniform(-50, 50)
        self.__vector = Vec3(x, y, z)

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_mid_material, 1)

        self.__task_name = f"raindrop_impact_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        dt = globalClock.getDt()
        pos = self.__node_path.getPos()
        pos += self.__vector * dt
        self.__node_path.setPos(pos)
        if 1 <= task.time:
            self.delete()
            return Task.done
        return Task.cont

    def delete(self) -> None:
        self.__node_path.removeNode()



class MissileBulletGraphics:
    """ミサイル弾頭の3Dモデル描画および軌跡パーティクル生成クラス。"""

    def __init__(self, base: MyApp, team_type: TeamType) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.model.missile_bullet.copyTo(base.render)
        )
        self.__node_path.setScale(3.0)

        team_graphics_setting = graphics_setting.get_team(team_type)
        material = team_graphics_setting.tank_mid_material
        self.__change_material(self.__node_path, "crayon_color", material)

    def __change_material(
        self, model: NodePath, target_material_name: str, new_material: Material
    ) -> None:
        for mat in model.findAllMaterials():
            if mat.getName() == target_material_name:
                model.replaceMaterial(mat, new_material)

    def update(self, pos: Point3, vector: Vec3) -> None:
        self.set_pos(pos)
        self.set_quat_from_direction(vector)

        particle_count = 4
        for _ in range(particle_count):
            offset = Vec3(
                fx_randomizer.uniform(-1.0, 1.0),
                fx_randomizer.uniform(-1.0, 1.0),
                fx_randomizer.uniform(-1.0, 1.0),
            )
            particle_pos = pos + offset
            dir_variation = Vec3(
                fx_randomizer.uniform(-0.5, 0.5),
                fx_randomizer.uniform(-0.5, 0.5),
                fx_randomizer.uniform(-0.5, 0.5),
            )
            particle_vector = vector.normalized() + dir_variation
            MissileBulletTrailGraphics(
                self.__base, self.__team_type, particle_pos, particle_vector, 3.0
            )

    def set_pos(self, pos: Point3) -> None:
        self.__node_path.setPos(pos)

    def set_quat_from_direction(self, vector: Vec3) -> None:
        up = Vec3(0, 0, 1)
        tmp = NodePath("tmp")
        tmp.lookAt(vector, up)
        hpr = tmp.getHpr()
        z = hpr[0]
        x = hpr[1] - 90.0
        y = hpr[2]
        self.__node_path.setHpr((z, x, y))

    def delete(self) -> None:
        self.__node_path.removeNode()


class MissileBulletTrailGraphics:
    """ミサイル飛翔時の煙・インク軌跡パーティクル。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        pos: Vec3,
        vector: Vec3,
        radius: float,
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m.copyTo(base.render)
        )
        self.__node_path.setPos(pos)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)

        self.__vector = -vector.normalized()
        self.__max_radius = radius * 0.5
        self.__min_radius = 0.1
        self.__life_time = 0.5
        self.__task_name = f"missile_trail_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        t = task.time / self.__life_time
        v = t**2

        scale = self.__max_radius + (self.__min_radius - self.__max_radius) * v
        self.__node_path.setScale(scale)

        alpha = 1.0 - v
        self.__node_path.setAlphaScale(alpha)

        particle_speed = 30.0
        pos = self.__node_path.getPos()
        dt = globalClock.getDt()
        pos += self.__vector * particle_speed * dt
        self.__node_path.setPos(pos)

        if task.time >= self.__life_time:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__node_path.removeNode()


class MissileImpactMarkerGraphics:
    """ミサイル落下予測地点の地面マーカー。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, pos: Point3
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cylinder_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(5.0, 5.0, 0.5)
        self.__node_path.setPos(pos)
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_dark_material, 1)

    def delete(self) -> None:
        self.__node_path.removeNode()


class MissileExplosionGraphics:
    """ミサイル着弾時の大爆発エフェクト。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, radius: float, pos: Vec3
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(radius)
        self.__node_path.setPos(pos)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        setting = graphics_setting.get_team(team_type)
        mat = Material("missile_explosion")
        mat.set_base_color(Vec4(*setting.paint_color_light.float_rgb_linear, 1))
        mat.set_metallic(0)
        mat.set_emission(Vec4(0, 0, 0, 1))
        mat.set_roughness(0.1)
        self.__node_path.setMaterial(mat, 1)

        self.__task_name = f"missile_explosion_{id(self)}"
        self.__base.taskMgr.add(self.__update_task, self.__task_name)

    def __update_task(self, task: Task.Task) -> int:
        duration = 1.0
        t = min(1.0, task.time / duration)
        v = t**2
        self.__node_path.setAlphaScale(1.0 - v)
        if task.time >= duration:
            self.delete()
            return Task.done
        return Task.cont

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)

    def delete(self) -> None:
        self.__node_path.removeNode()


class RainBulletGraphics:
    """雨ふらしの雨雲メッシュおよび地面照射範囲描画。"""

    def __init__(
        self,
        base: MyApp,
        physics_world: BulletWorld,
        team_type: TeamType,
        radius: float,
    ) -> None:
        self.__base = base
        self.__rain_ground_circle_graphics = RainGroundCircleGraphics(
            base, physics_world, team_type, radius
        )

    def update(self, pos: Vec3) -> None:
        self.__rain_ground_circle_graphics.update(pos)

    def delete(self) -> None:
        self.__rain_ground_circle_graphics.fade_out()


class RainGroundCircleGraphics:
    """雨ふらしの地面範囲サークルライン描画。"""

    def __init__(
        self,
        base: MyApp,
        physics_world: BulletWorld,
        team_type: TeamType,
        radius: float,
    ) -> None:
        self.__base = base
        self.__physics_world = physics_world
        self.__radius = radius
        setting = graphics_setting.get_team(team_type)
        self.__color = setting.paint_color_light
        self.__node_path: NodePath = base.render.attachNewNode("rain_ground_circle")

    def update(self, center: Vec3) -> None:
        segments = 16
        radius = self.__radius + 0.1
        points: list[Point3] = []

        for i in range(segments):
            theta = 2.0 * math.pi * (i / segments)
            x = center.x + radius * math.cos(theta)
            y = center.y + radius * math.sin(theta)

            from_pos = Vec3(x, y, center.z + 100.0)
            to_pos = Vec3(x, y, center.z - 100.0)

            result = self.__physics_world.rayTestClosest(from_pos, to_pos)
            if not result.hasHit():
                points.append(Vec3(x, y, center.z + 0.5))
                continue                
            if result.getNode().getPythonTag("collision_group") in (CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_EMP):
                points.append(Vec3(x, y, center.z + 0.5))
                continue
            points.append(result.getHitPos() + Vec3(0, 0, 0.5))

        self.__node_path.removeNode()
        self.__node_path = self.__make_circle_polyline(points)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)

    def __make_circle_polyline(self, points: list[Point3]) -> NodePath:
        ls = LineSegs()
        ls.setThickness(3)
        ls.setColor(self.__color.float_rgb + (1.0,))

        for i in range(len(points)):
            ls.moveTo(points[i])
            ls.drawTo(points[(i + 1) % len(points)])

        return self.__base.render.attachNewNode(ls.create())

    def fade_out(self) -> None:
        self.__task_name = f"rain_circle_fade_{id(self)}"
        self.__base.taskMgr.add(self.__fade_out_task, self.__task_name)

    def __fade_out_task(self, task: Task.Task) -> int:
        duration = 0.5
        t = task.time / duration
        v = t**2
        self.__node_path.setAlphaScale(1.0 - v)
        if task.time >= duration:
            self.delete()
            return Task.done
        return Task.cont

    def delete(self) -> None:
        self.__node_path.removeNode()


class RainDropBulletGraphics:
    """落下するインク雨粒の3Dメッシュ描画。"""

    def __init__(self, base: MyApp, team_type: TeamType) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m.copyTo(base.render)
        )
        self.__node_path.setScale(1.0, 1.0, 5.0)
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)

    def set_pos(self, pos: Point3) -> None:
        self.__node_path.setPos(pos)

    def impact(self) -> None:
        pos = self.__node_path.getPos()
        particle_count = 3
        for _ in range(particle_count):
            offset = Vec3(
                fx_randomizer.uniform(-1.0, 1.0),
                fx_randomizer.uniform(-1.0, 1.0),
                fx_randomizer.uniform(-1.0, 1.0),
            )
            particle_pos = pos + offset
            dir_variation = Vec3(
                fx_randomizer.uniform(-10.0, 10.0),
                fx_randomizer.uniform(-10.0, 10.0),
                50.0,
            )
            RainDropImpactGraphics(
                self.__base, self.__team_type, particle_pos, dir_variation
            )

    def delete(self) -> None:
        self.__node_path.removeNode()


class RainDropImpactGraphics:
    """雨粒着弾時の小飛沫パーティクル。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, pos: Vec3, vector: Vec3
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m.copyTo(base.render)
        )
        self.__node_path.setScale(1.0)
        self.__node_path.setPos(pos)
        self.__vector = vector
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_mid_material, 1)
        self.__gravity = -98.0 * 2.0
        self.__task_name = f"raindrop_impact_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        dt = globalClock.getDt()
        pos = self.__node_path.getPos()
        self.__vector += Vec3(0, 0, self.__gravity) * dt
        pos += self.__vector * dt
        self.__node_path.setPos(pos)
        if pos.z <= 0:
            self.delete()
            return Task.done
        return Task.cont

    def delete(self) -> None:
        self.__node_path.removeNode()


class RainUpdraftGraphics:
    def __init__(self, base: MyApp, team_type: TeamType, pos: Point3) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__pos = pos
        self.__generated_count: int = 0
        self.__per_second = 8.0

    def update(self, effect_time: float) -> None:
        target_count = int(effect_time * self.__per_second)
        spawn_count = target_count - self.__generated_count
        for _ in range(spawn_count):
            ParticleRainUpdraftGraphics(self.__base, self.__team_type, self.__pos)
        self.__generated_count = target_count


class ParticleRainUpdraftGraphics:
    def __init__(self, base: MyApp, team_type: TeamType, pos: Vec3) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m.copyTo(base.render)
        )
        self.__node_path.setScale(2)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        self.__node_path.setAlphaScale(0.8)

        pos_offset = Vec3(fx_randomizer.uniform(-3.0, 3.0), fx_randomizer.uniform(-3.0, 3.0), 0.0)
        self.__node_path.setPos(pos + pos_offset)
        
        x = fx_randomizer.uniform(-0.5, 0.5)
        y = fx_randomizer.uniform(-0.5, 0.5)
        z = fx_randomizer.uniform(150, 180)
        self.__vector = Vec3(x, y, z)

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_mid_material, 1)

        self.__task_name = f"raindrop_impact_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        dt = globalClock.getDt()
        t = task.time
        pos = self.__node_path.getPos()
        pos += self.__vector * dt
        self.__node_path.setPos(pos)
        if 200 <= pos.z:
            self.delete()
            return Task.done
        return Task.cont

    def delete(self) -> None:
        self.__node_path.removeNode()


class ElectromagneticWaveBulletGraphics:
    """電磁波の拡大リングポリライン描画。"""

    def __init__(self, base: MyApp, team_type: TeamType, pos: Vec3) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = base.render.attachNewNode("circle")
        self.__pos = pos
        setting = graphics_setting.get_team(team_type)
        self.__color = setting.paint_color_light

    def update(self, radius: float) -> None:
        self.__node_path.removeNode()
        self.__node_path = self.__make_circle_polyline(radius)
        self.__node_path.setPos(self.__pos)

    def __make_circle_polyline(self, radius: float) -> NodePath:
        ls = LineSegs()
        ls.setThickness(4)
        ls.setColor(self.__color.float_rgb + (1.0,))

        for i in range(33):
            theta = 2.0 * math.pi * (i / 32)
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            ls.drawTo(x, y, 0.5)
        return self.__base.render.attachNewNode(ls.create())

    def delete(self) -> None:
        self.__node_path.removeNode()


class HyperBeamBulletPreGraphics:
    """ハイパービームの予備光線描画。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        pos: Vec3,
        direction: Vec3,
        radius: float,
        bullet_range: float,
    ) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m_origin.copyTo(
                base.render
            )
        )
        self.__node_path.setPos(pos)
        self.__node_path.setHpr(self.__hpr_from_direction(direction))
        self.__node_path.setScale(
            bullet_range * 0.5, radius * 0.5, radius * 0.5
        )

        self.__bullet_range = bullet_range
        self.__radius = radius

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_light_material, 1)

    def update(self, state_frame: int, state_time: float):
        if state_frame % 2 == 0:
            self.__node_path.show()
        else:
            self.__node_path.hide()
        
        end_radius = 0.1
        start_radius = self.__radius
        duration = 1.0
        t = state_time / duration
        t = min(t, 1.0)
        v = t
        radius = start_radius + (end_radius - start_radius) * v
        self.__node_path.setScale(
            self.__bullet_range * 0.5, radius * 0.5, radius * 0.5
        )

    def __hpr_from_direction(self, direction: Vec3) -> VBase3:
        tmp = NodePath("tmp")
        tmp.lookAt(direction, Vec3(0, 0, 1))
        hpr = tmp.getHpr()
        hpr.setX(hpr.x + 90)
        return hpr

    def delete(self) -> None:
        self.__node_path.removeNode()


class HyperBeamBulletGraphics:
    """ハイパービームの3D巨大直方体光線描画。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        pos: Vec3,
        direction: Vec3,
        radius: float,
        bullet_range: float,
    ) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m_origin.copyTo(
                base.render
            )
        )
        self.__node_path.setPos(pos)
        self.__node_path.setHpr(self.__hpr_from_direction(direction))
        self.__node_path.setScale(
            bullet_range * 0.5, radius, radius
        )
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        self.__node_path.setAlphaScale(0.7)

        self.__bullet_range = bullet_range
        self.__radius = radius
        self.__direction = direction

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_light_material, 1)

        self.__timer = 0.0
        self.__shock_wave_list = []

    def update(self, state_time: float, dt: float) -> None:
        expand_duration = 0.1
        start_radius = 0.1
        end_radius = self.__radius
        t = state_time / expand_duration
        t = min(t, 1.0)
        v = t
        radius = start_radius + (end_radius - start_radius) * v
        self.__node_path.setScale(
            self.__bullet_range * 0.5, radius, radius
        )

        shoke_wave_interval = 0.1
        self.__timer += dt
        if shoke_wave_interval <= self.__timer:
            self.__timer -= shoke_wave_interval
            shoke_wave = HyperBeamBulletShockWaveGraphics(
                self.__base,
                self.__team_type,
                self.__node_path.getPos(),
                self.__direction,
                self.__radius,
                self.__bullet_range,
            )
            self.__shock_wave_list.append(shoke_wave)
        for shock_wave in self.__shock_wave_list:
            shock_wave.update(dt)
        self.__shock_wave_list = [shock_wave for shock_wave in self.__shock_wave_list if not shock_wave.is_finished]
        

    def __hpr_from_direction(self, direction: Vec3) -> VBase3:
        tmp = NodePath("tmp")
        tmp.lookAt(direction, Vec3(0, 0, 1))
        hpr = tmp.getHpr()
        hpr.setX(hpr.x + 90)
        return hpr

    def delete(self) -> None:
        self.__node_path.removeNode()
        for shock_wave in self.__shock_wave_list:
            shock_wave.delete()


class HyperBeamBulletShockWaveGraphics:
    """ハイパービームの衝撃波ポリゴン描画。"""
    
    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        pos: Vec3,
        direction: Vec3,
        radius: float,
        bullet_range: float,
    ) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setPos(pos)
        self.__node_path.setHpr(self.__hpr_from_direction(direction))
        self.__node_path.setScale(
            radius * 0.2, radius * 1.2, radius * 1.2
        )

        self.__initial_pos = pos
        self.__direction = direction

        self.__bullet_range = bullet_range
        self.__radius = radius

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.tank_mid_material, 1)

        self.__timer = 0.0
        self.__is_finished = False

    @property
    def is_finished(self) -> bool:
        return self.__is_finished

    def update(self, dt: float) -> None:
        speed = 500.0
        direction = self.__direction.normalized()
        self.__timer += dt
        move_vector = direction * speed * self.__timer
        current_pos = self.__initial_pos + move_vector
        self.__node_path.setPos(current_pos)
        distance = move_vector.length()
        if self.__bullet_range <= distance:
            self.delete()
            self.__is_finished = True

    def __hpr_from_direction(self, direction: Vec3) -> VBase3:
        tmp = NodePath("tmp")
        tmp.lookAt(direction, Vec3(0, 0, 1))
        hpr = tmp.getHpr()
        hpr.setX(hpr.x + 90)
        return hpr

    def delete(self) -> None:
        self.__node_path.removeNode()