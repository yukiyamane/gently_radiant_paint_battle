"""弾丸着弾時のダメージポップアップテキスト描画モジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.core import NodePath, Point2, Point3, TextNode

from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.graphics.setting import graphics_setting, HUDTextKey
from paint_battle_custom_tank.shared.util.randomizer import fx_randomizer

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


class BulletDamageText:
    """3Dワールド空間の被弾位置に2Dテキストを追従・浮上表示するクラス。"""

    def __init__(
        self,
        base: MyApp,
        team_type: TeamType,
        damage_amount: int,
        world_pos: Point3,
    ) -> None:
        self.__base = base
        self.__timer = 0.0
        self.__initial_pos = (0.0, 0.0)
        self.__text: Optional[OnscreenText] = None
        self.__task_name = f"damage_text_{id(self)}"
        self.__create(team_type, damage_amount, world_pos)

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
        self, team_type: TeamType, amount: int, world_pos: Point3
    ) -> None:
        height_offset = 5.0
        pos2d = self.__world_to_aspect2d(world_pos, height_offset)
        if pos2d is None:
            return
        x, _, z = pos2d
        self.__initial_pos = (x, z)

        setting = graphics_setting.get_team(team_type)
        color = setting.paint_color_light.float_rgb

        self.__text = OnscreenText(
            text=str(round(amount / 10.0, 1)),
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
        if self.__text is not None:
            self.__text.removeNode()
            self.__text.destroy()
            self.__text = None


