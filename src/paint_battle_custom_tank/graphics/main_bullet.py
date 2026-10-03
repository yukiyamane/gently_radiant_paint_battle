"""メインおよびサブ武器用弾丸・ヒットエフェクト描画モジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.core import Material, NodePath, Point3, TransparencyAttrib, Vec3, Vec4

from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.graphics.setting import graphics_setting

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


class BounceBulletGraphics:
    """バウンス弾の3D球体メッシュ描画クラス。"""

    def __init__(self, base: MyApp, team_type: TeamType, radius: float) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__radius = radius
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(radius)
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)

    def update(self, pos: Vec3) -> None:
        self.set_pos(pos)

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)

    def delete(self) -> None:
        self.__node_path.removeNode()


class BounceBulletHitGraphics:
    """バウンス弾着弾時の拡大小エフェクト。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, pos: Point3, radius: float
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(0.1)
        self.__node_path.setPos(pos)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        self.__node_path.setAlphaScale(0.5)
        self.__radius = radius

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)
        self.__task_name = f"bounce_bullet_hit_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        duration = 0.2
        min_radius = self.__radius * 2.0
        max_radius = self.__radius * 3.0
        v = task.time / duration
        scale = (max_radius - min_radius) * v + min_radius
        self.__node_path.setScale(scale)
        if task.time >= duration:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__node_path.removeNode()


class ExplodingBulletGraphics:
    """爆発弾の3D球体メッシュ描画クラス。"""

    def __init__(self, base: MyApp, team_type: TeamType, radius: float) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(radius)
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)

    def delete(self) -> None:
        self.__node_path.removeNode()


class ExplodingExplosionGraphics:
    """爆発弾の爆発球体エフェクト（拡大とフェードアウト）。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, radius: float, pos: Point3
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
        self.__node_path.setMaterial(setting.bullet_material, 1)
        self.__task_name = f"exploding_explosion_{id(self)}"
        self.__base.taskMgr.add(self.__update_task, self.__task_name)

    def __update_task(self, task: Task.Task) -> int:
        duration = 0.5
        t = task.time / duration
        alpha = 1.0 - (t**2)
        self.__node_path.setAlphaScale(alpha)
        if task.time >= duration:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__node_path.removeNode()


class ThreeWayBulletGraphics:
    """3方向拡散弾の3D球体メッシュ描画クラス。"""

    def __init__(self, base: MyApp, team_type: TeamType, radius: float) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(radius)
        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)

    def update(self, pos: Vec3) -> None:
        self.set_pos(pos)

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)

    def delete(self) -> None:
        self.__node_path.removeNode()


class ThreeWayBulletHitGraphics:
    """3方向弾着弾時の拡大小エフェクト。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, pos: Point3, radius: float
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(0.1)
        self.__node_path.setPos(pos)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        self.__node_path.setAlphaScale(0.5)
        self.__radius = radius

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)
        self.__task_name = f"threeway_bullet_hit_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        duration = 0.2
        min_radius = self.__radius * 2.0
        max_radius = self.__radius * 3.0
        v = task.time / duration
        scale = (max_radius - min_radius) * v + min_radius
        self.__node_path.setScale(scale)
        if task.time >= duration:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__node_path.removeNode()


class LaserBulletGraphics:
    """レーザーの3Dシリンダー伸長メッシュ描画クラス。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        radius: float,
        pos: Point3,
        hpr: Vec3,
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.cube_2m_origin.copyTo(
                base.render
            )
        )
        self.__radius = radius
        self.__node_path.setPos(pos)
        self.__node_path.setHpr(hpr)
        self.__node_path.setScale(self.__radius)

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)

    def update(self, length: float) -> None:
        self.__node_path.setScale(length * 0.5, self.__radius, self.__radius)

    def delete(self) -> None:
        self.__node_path.removeNode()


class LaserBulletHitGraphics:
    """レーザー着弾時の拡大小エフェクト。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, pos: Point3, radius: float
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(0.1)
        self.__node_path.setPos(pos)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)
        self.__node_path.setAlphaScale(0.5)
        self.__radius = radius

        setting = graphics_setting.get_team(team_type)
        self.__node_path.setMaterial(setting.bullet_material, 1)
        self.__task_name = f"laser_bullet_hit_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        duration = 0.2
        min_radius = self.__radius * 2.0
        max_radius = self.__radius * 3.0
        v = task.time / duration
        scale = (max_radius - min_radius) * v + min_radius
        self.__node_path.setScale(scale)
        if task.time >= duration:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__node_path.removeNode()