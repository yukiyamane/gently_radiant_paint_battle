"""戦車本体および撃破爆発エフェクトの3D描画モジュール。"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from direct.task import Task
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
# pyrefly: ignore [missing-import]
from panda3d.core import (
    Material,
    NodePath,
    Point2,
    Point3,
    TextNode,
    TransparencyAttrib,
    VBase3,
    Vec3,
    Vec4,
)



from paint_battle_custom_tank.core.setting import TeamType, WeaponType, TeamSettingFactory
from paint_battle_custom_tank.core.special_weapon_setting import SpecialWeaponSettingFactory
from paint_battle_custom_tank.graphics.setting import graphics_setting, HUDTextKey
from paint_battle_custom_tank.shared.util.path_manager import PathManager
from paint_battle_custom_tank.shared.util.randomizer import fx_randomizer

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


class TankGraphics:
    """戦車モデル（本体・メイン砲塔・左右サブ砲塔）の組み立てと描画管理クラス。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        main: WeaponType,
        sub_left: WeaponType,
        sub_right: WeaponType,
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = self.__base.render.attachNewNode("tank")

        registry = {
            WeaponType.BOUNCE: "bounce",
            WeaponType.EXPLODING: "exploding",
            WeaponType.THREE_WAY: "three_way",
            WeaponType.LASER: "laser",
        }

        self.__main = self.__base.loader.loadModel(
            PathManager.resource_vfs(f"models/main_{registry[main]}.glb")
        )
        self.__main.reparentTo(self.__node_path)

        self.__sub_left = self.__base.loader.loadModel(
            PathManager.resource_vfs(f"models/sub_{registry[sub_left]}.glb")
        )
        self.__sub_left.reparentTo(self.__node_path)
        self.__sub_left.setPos(Vec3(-13, 0, 0))

        self.__sub_right = self.__base.loader.loadModel(
            PathManager.resource_vfs(f"models/sub_{registry[sub_right]}.glb")
        )
        self.__sub_right.reparentTo(self.__node_path)
        self.__sub_right.setPos(Vec3(13, 0, 0))

        team_graphics_setting = graphics_setting.get_team(team_type)
        mat_mid = team_graphics_setting.tank_mid_material
        mat_light = team_graphics_setting.tank_light_material
        mat_dark = team_graphics_setting.tank_dark_material

        for model in (self.__main, self.__sub_left, self.__sub_right):
            self.__change_material(model, "tank_mid", mat_mid)
            self.__change_material(model, "tank_light", mat_light)
            self.__change_material(model, "tank_dark", mat_dark)

    def __change_material(
        self, model: NodePath, target_material_name: str, new_material: Material
    ) -> None:
        for mat in model.findAllMaterials():
            if mat.getName() == target_material_name:
                model.replaceMaterial(mat, new_material)

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)

    def set_hpr(self, hpr: VBase3) -> None:
        self.__node_path.setHpr(hpr)

    def remove(self) -> None:
        self.__node_path.removeNode()


class TankDeathExplosionGraphics:
    """戦車撃破時の拡大・フェードアウト爆発球体エフェクト。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, pos: Point3
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            base.resource_context.primitive_model.ico_sphere_2m.copyTo(
                base.render
            )
        )
        self.__node_path.setScale(10.0)
        self.__node_path.setPos(pos)
        self.__node_path.setTransparency(TransparencyAttrib.MAlpha)

        team_graphics_setting = graphics_setting.get_team(team_type)
        mat = Material("death_explosion")
        mat.set_base_color(
            Vec4(*team_graphics_setting.paint_color_light.float_rgb_linear, 1)
        )
        mat.set_metallic(0)
        mat.set_emission(Vec4(0, 0, 0, 1))
        mat.set_roughness(0.1)
        self.__node_path.setMaterial(mat, 1)

        self.__task_name = f"tank_death_explosion_{id(self)}"
        self.__base.taskMgr.add(self.__update_task, self.__task_name)

    def __update_task(self, task: Task.Task) -> int:
        duration = 1.0
        first_radius = 16.0
        last_radius = 50.0
        t = task.time / duration
        scale = (last_radius - first_radius) * t + first_radius
        self.__node_path.setScale(scale)
        alpha = 1.0 - (t**2)
        self.__node_path.setAlphaScale(alpha)

        if task.time >= duration:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        self.__node_path.removeNode()


class SpecialActivationUI:
    def __init__(self, base: MyApp, team_type: TeamType, world_pos: Point3):
        self.__base = base
        self.__particle_list = []
        for i in range(4):
            degree = i * 90.0 + fx_randomizer.uniform(-15.0, 15.0)
            particle = ParticleSpecialBurstEffect(base, degree, world_pos)
            self.__particle_list.append(particle)
        self.__text = SpecialActivationText(base, team_type, world_pos)

        self.__duration = 0.5

        self.__task_name = f"special_activation_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        for p in self.__particle_list:
            p.update(task.time)
        if task.time >= self.__duration:
            return Task.done
        return Task.cont



class SpecialActivationText:
    """3Dワールド空間の被弾位置に2Dテキストを追従・浮上表示するクラス。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        world_pos: Point3,
    ) -> None:
        self.__base = base
        self.__timer = 0.0
        self.__initial_pos = (0.0, 0.0)
        self.__text: Optional[OnscreenText] = None
        self.__task_name = f"special_text_{id(self)}"
        self.__create(team_type, world_pos)

    def __world_to_aspect2d(
        self, world_pos: Point3, height_offset: float
    ) -> Optional[Point3]:
        pos = Point3(world_pos.x, world_pos.y, world_pos.z + height_offset)
        p3 = self.__base.cam.getRelativePoint(self.__base.render, pos)
        p2 = Point2()
        if not self.__base.camLens.project(p3, p2):
            return None
        r2d = Point3(p2.x, 0, p2.y)
        a2d = self.__base.aspect2d.getRelativePoint(self.__base.render2d, r2d)
        return a2d

    def __create(
        self, team_type: TeamType, world_pos: Point3
    ) -> None:
        height_offset = 5.0
        pos2d = self.__world_to_aspect2d(world_pos, height_offset)
        if pos2d is None:
            return
        x, _, z = pos2d
        self.__initial_pos = (x, z)

        setting = graphics_setting.get_team(team_type)
        color = setting.paint_color_light.float_rgb
        
        team_setting = TeamSettingFactory.create(team_type)
        special_weapon_setting = SpecialWeaponSettingFactory.create(
            team_setting.tank_special_weapon_type
        )
        special_text = special_weapon_setting.name_dict[graphics_setting.language]

        self.__text = OnscreenText(
            text=special_text,
            pos=(x, z),
            scale=0.08,
            fg=color + (1.0,),
            shadow=(0, 0, 0, 1),
            shadowOffset=(0.05, 0.05),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_regular,
            mayChange=True,
            parent=self.__base.aspect2d,
        )
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        duration = 1.0
        t = task.time / duration
        v = 1.0 - (1.0 - t) * (1.0 - t)
        max_z_offset = 0.05
        new_z = self.__initial_pos[1] + v * max_z_offset
        if self.__text:
            self.__text.setY(new_z)

        if task.time >= duration:
            self.__delete()
            return Task.done
        return Task.cont

    def __delete(self) -> None:
        if self.__text:
            self.__text.removeNode()
            self.__text.destroy()
            self.__text = None


class ParticleSpecialBurstEffect:
    """個別のクラッシュライン。"""

    def __init__(
        self, base: MyApp, degree: float, world_pos: Point3
    ) -> None:
        self.__base = base
        self.__spawn_time = 0
        self.__degree = degree

        pos2d = self.__world_to_aspect2d(world_pos, height_offset=5.0)
        if pos2d is None:
            return
        x, _, z = pos2d
        self.__initial_pos = (x, _, z)

        self.__node_path: NodePath = base.aspect2d.attachNewNode("ParticleClash")
        self.__frame = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-0.0, 0.0, -0.0125, 0.0125),
            pos=(0, 0, 0),
            parent=self.__node_path,
        )
        self.__node_path.setPos(self.__initial_pos)
        self.__node_path.setHpr(0, 0, degree)

        self.__min_length = 0.0
        self.__max_length = 0.5
        self.__stretch_duration = 0.15
        self.__shrink_duration = 0.15

    def __world_to_aspect2d(
        self, world_pos: Point3, height_offset: float
    ) -> Optional[Point3]:
        pos = Point3(world_pos.x, world_pos.y, world_pos.z + height_offset)
        p3 = self.__base.cam.getRelativePoint(self.__base.render, pos)
        p2 = Point2()
        if not self.__base.camLens.project(p3, p2):
            return None
        r2d = Point3(p2.x, 0, p2.y)
        a2d = self.__base.aspect2d.getRelativePoint(self.__base.render2d, r2d)
        return a2d

    def update(self, effect_time: float) -> None:
        elapsed = effect_time - self.__spawn_time
        if elapsed < 0.0:
            return

        if elapsed < self.__stretch_duration:
            t = elapsed / self.__stretch_duration
            length = self.__min_length + (self.__max_length - self.__min_length) * t
            self.__frame["frameSize"] = (-0.0, length, -0.0125, 0.0125)
        elif elapsed < (self.__stretch_duration + self.__shrink_duration):
            shrink_elapsed = elapsed - self.__stretch_duration
            t = shrink_elapsed / self.__shrink_duration
            length = self.__min_length + (self.__max_length - self.__min_length) * t
            self.__frame["frameSize"] = (length, self.__max_length, -0.0125, 0.0125)
        else:
            self.destroy()

    def destroy(self) -> None:
        self.__node_path.removeNode()
