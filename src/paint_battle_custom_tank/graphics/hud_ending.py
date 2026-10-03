"""試合終了（Finish!演出）および結果発表（リザルト画面・勝敗・紙吹雪）UIモジュール。"""

from __future__ import annotations
import math
from typing import TYPE_CHECKING
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.core import NodePath, Point3, TextNode

from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.graphics.setting import HUDTextKey, graphics_setting
from paint_battle_custom_tank.shared.util.randomizer import fx_randomizer
from paint_battle_custom_tank.shared.util.yamane_prepare import globalClock

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import TankStatus
    from paint_battle_custom_tank.core.team import Team
    from paint_battle_custom_tank.main import MyApp


class BattleFinishUI:
    """試合終了時の「Finish! / おしまい！」帯スライド演出UI。"""

    def __init__(self, base: MyApp) -> None:
        self.__base = base
        self.__particle_list: list[ParticleFinish] = []

    def start(self) -> None:
        self.__particle_list.append(
            ParticleFinish(self.__base, 0, Point3(0, 0, -0.3), 5.0, 1.0, -1)
        )
        self.__particle_list.append(
            ParticleFinish(self.__base, 1, Point3(0.1, 0, 0.3), -3.0, 0.8, 1)
        )
        self.__particle_list.append(
            ParticleFinish(self.__base, 2, Point3(-0.2, 0, 0.7), 2.0, 0.9, -1)
        )
        self.__particle_list.append(
            ParticleFinish(self.__base, 3, Point3(0.2, 0, -0.8), -4.0, 0.7, 1)
        )

    def update(self, after_game_time: float) -> None:
        for particle in self.__particle_list:
            particle.update(after_game_time)

    def destroy(self) -> None:
        for particle in self.__particle_list:
            particle.destroy()
        self.__particle_list.clear()


class ParticleFinish:
    """個別のFinish帯アニメーションパーツ。"""

    def __init__(
        self,
        base: MyApp,
        index: int,
        pos: Point3,
        degree: float,
        scale: float,
        direction: int,
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = base.aspect2d.attachNewNode("ParticleFinish")
        self.__node_path_offset: NodePath = (
            self.__node_path.attachNewNode("ParticleFinishPos")
        )

        self.__index = index
        self.__node_path.setPos(pos)
        self.__node_path.setScale(scale)
        self.__node_path.setHpr(0, 0, degree)

        self.__direction = direction
        self.__duration_slide = 0.3 * fx_randomizer.uniform(0.7, 1.3)

        finish_text = graphics_setting.get_text(HUDTextKey.FINISH)

        if self.__index % 2 == 0:
            color = graphics_setting.alpha.paint_color.float_rgb
        else:
            color = graphics_setting.bravo.paint_color.float_rgb
        self.__direct_frame_back = DirectFrame(
            frameSize=(-3.1, 3.1, -0.13, 0.13),
            frameColor=(1, 1, 1, 1),
            pos=(0, 0, 0),
            scale=1,
            parent=self.__node_path_offset,
        )
        self.__direct_frame = DirectFrame(
            frameSize=(-3.0, 3.0, -0.12, 0.12),
            frameColor=color + (1,),
            pos=(0, 0, 0),
            scale=1,
            parent=self.__node_path_offset,
        )

        for i in range(5):
            x = 0.8 * i - 1.6
            OnscreenText(
                text=finish_text,
                pos=(x, -0.05),
                scale=0.15,
                fg=(1, 1, 1, 1),
                align=TextNode.ACenter,
                font=self.__base.resource_context.font.mplus_bold,
                parent=self.__node_path_offset,
                sort=10,
            )

    def update(self, after_game_time: float) -> None:
        if after_game_time <= self.__duration_slide:
            t_slide = after_game_time / self.__duration_slide
            v_slide = 1.0 - (1.0 - t_slide) ** 2
            min_pos = 3.5 * self.__direction
            max_pos = 0.0
            x = min_pos + (max_pos - min_pos) * v_slide
            self.__node_path_offset.setPos(x, 0, 0)
        else:
            self.__node_path_offset.setPos(0, 0, 0)

    def destroy(self) -> None:
        self.__node_path.removeNode()


class BattleResultHUD:
    """試合結果画面（塗りゲージ・勝敗表示・個人成績・紙吹雪・クラッシュ演出）統括クラス。"""

    def __init__(self, base: MyApp, battle: Battle) -> None:
        self.__base = base
        self.__battle = battle
        self.__paint_coverage_ui = PaintCoverageUI(base, battle)

        winner_team_type = self.__battle.status.winner_team_type
        if winner_team_type is None:
            winner_team_type = TeamType.ALPHA

        self.__winner_text = WinnerUI(base, winner_team_type)
        self.__team_result_ui_dict: dict[TeamType, TeamResultUI] = {
            TeamType.ALPHA: TeamResultUI(
                base, TeamType.ALPHA, self.__battle.team_dict[TeamType.ALPHA]
            ),
            TeamType.BRAVO: TeamResultUI(
                base, TeamType.BRAVO, self.__battle.team_dict[TeamType.BRAVO]
            ),
        }
        self.__confetti = Confetti(self.__base, winner_team_type)
        self.__clash = Clash(self.__base, winner_team_type)

    def update(self, result_time: float) -> None:
        self.__paint_coverage_ui.update(result_time)
        self.__winner_text.update(result_time)
        for ui in self.__team_result_ui_dict.values():
            ui.update(result_time)
        self.__confetti.update(result_time)
        self.__clash.update(result_time)


class PaintCoverageUI:
    """結果画面用ペイント占有率ゲージ。"""

    def __init__(
        self, base: MyApp, battle: Battle
    ) -> None:
        self.__base = base
        self.__battle = battle
        self.__node_path: NodePath = base.aspect2d.attachNewNode("PaintCoverageUI")
        z = -0.775

        alpha_team_setting = graphics_setting.get_team(TeamType.ALPHA)
        bravo_team_setting = graphics_setting.get_team(TeamType.BRAVO)

        alpha_color = alpha_team_setting.paint_color.float_rgb
        bravo_color = bravo_team_setting.paint_color.float_rgb

        alpha_ratio = self.__battle.stage.paint_stage.status.alpha_ratio
        self.__alpha_percentage = round(alpha_ratio * 100.0, 1)
        alpha_area = self.__battle.stage.paint_stage.status.alpha_area
        self.__alpha_area = f"{round(alpha_area / 100, 1)}m²"

        bravo_ratio = self.__battle.stage.paint_stage.status.bravo_ratio
        self.__bravo_percentage = round(bravo_ratio * 100.0, 1)
        bravo_area = self.__battle.stage.paint_stage.status.bravo_area
        self.__bravo_area = f"{round(bravo_area / 100, 1)}m²"

        basis = 1.69
        alpha_length = -basis + (basis * 2.0) * alpha_ratio
        bravo_length = basis - (basis * 2.0) * bravo_ratio

        self.__frame_back = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-1.7, 1.7, -0.175, 0.175),
            pos=(0, 0, z),
            parent=self.__node_path,
        )
        self.__alpha_bar = DirectFrame(
            frameColor=alpha_color + (1.0,),
            frameSize=(-1.69, alpha_length, -0.165, 0.165),
            pos=(0, 0, z),
            parent=self.__node_path,
        )
        self.__alpha_text = OnscreenText(
            text=f"{self.__alpha_percentage}%",
            pos=(-1.65, z + 0.02),
            scale=0.16,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )
        self.__alpha_area_text = OnscreenText(
            text=self.__alpha_area,
            pos=(-1.65, z - 0.12),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )


        self.__bravo_bar = DirectFrame(
            frameColor=bravo_color + (1.0,),
            frameSize=(bravo_length, 1.69, -0.165, 0.165),
            pos=(0, 0, z),
            parent=self.__node_path,
        )
        self.__bravo_text = OnscreenText(
            text=f"{self.__bravo_percentage}%",
            pos=(1.65, z + 0.02),
            scale=0.16,
            fg=(1, 1, 1, 1),
            align=TextNode.ARight,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )
        self.__bravo_area_text = OnscreenText(
            text=self.__bravo_area,
            pos=(1.65, z - 0.12),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ARight,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )

        self.__frame_back.hide()
        self.__alpha_bar.hide()
        self.__alpha_text.hide()
        self.__alpha_area_text.hide()
        self.__bravo_bar.hide()
        self.__bravo_text.hide()
        self.__bravo_area_text.hide()

        self.__is_frame_back_shown = False
        self.__is_alpha_bar_shown = False
        self.__is_alpha_text_shown = False
        self.__is_bravo_bar_shown = False
        self.__is_bravo_text_shown = False

    def update(self, result_time: float) -> None:
        if not self.__is_frame_back_shown and result_time >= 1.0:
            self.__frame_back.show()
            self.__is_frame_back_shown = True
        if not self.__is_alpha_bar_shown and result_time >= 2.0:
            self.__alpha_bar.show()
            self.__is_alpha_bar_shown = True
        if not self.__is_alpha_text_shown and result_time >= 2.2:
            self.__alpha_text.show()
            self.__alpha_area_text.show()
            self.__is_alpha_text_shown = True
        if not self.__is_bravo_bar_shown and result_time >= 3.0:
            self.__bravo_bar.show()
            self.__is_bravo_bar_shown = True
        if not self.__is_bravo_text_shown and result_time >= 3.2:
            self.__bravo_text.show()
            self.__bravo_area_text.show()
            self.__is_bravo_text_shown = True


class WinnerUI:
    """勝者チーム名のポップアップ表示。"""

    def __init__(self, base: MyApp, winner_team_type: TeamType) -> None:
        self.__base = base
        self.__node_path: NodePath = base.aspect2d.attachNewNode("WinnerUI")

        team_setting = graphics_setting.get_team(winner_team_type)
        text_color = team_setting.paint_color.float_rgb
        team_name = team_setting.get_name(graphics_setting.language)

        win_word = graphics_setting.get_text(HUDTextKey.WINNER_PREFIX)
        letter = f"{win_word}{team_name}"

        self.__text = OnscreenText(
            text=letter,
            pos=(0, -0.4),
            scale=0.4,
            fg=text_color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold_hq,
            parent=self.__node_path,
            sort=10,
        )
        offset_list = [(-0.01, -0.01), (0.01, -0.01), (0.01, 0.01), (-0.01, 0.01)]
        for i in range(4):
            offset = offset_list[i]
            text_border = OnscreenText(
                text=letter,
                pos=(offset[0], -0.4 + offset[1]),
                scale=0.4,
                fg=(0, 0, 0, 1),
                align=TextNode.ACenter,
                font=self.__base.resource_context.font.mplus_bold_hq,
                parent=self.__node_path,
                sort=9,
            )

        self.__node_path.hide()
        self.__is_text_shown = False

    def update(self, result_time: float) -> None:
        if not self.__is_text_shown and result_time >= 4.0:
            self.__node_path.show()
            self.__is_text_shown = True

    def destroy(self) -> None:
        self.__node_path.removeNode()


class TeamResultUI:
    """チーム成績コンテナ。"""

    def __init__(self, base: MyApp, team_type: TeamType, team: Team) -> None:
        self.__base = base
        self.__team_type = team_type
        self.__team = team
        self.__is_shown = False

    def update(self, result_time: float) -> None:
        if not self.__is_shown and result_time >= 6.0:
            tank_status = self.__team.tank_list[0].status
            TankResultUI(self.__base, self.__team_type, tank_status)
            self.__is_shown = True


class TankResultUI:
    """個人戦績（塗った面積・キル・デス・SP使用数）カードUI。"""

    def __init__(
        self, base: MyApp, team_type: TeamType, tank_status: TankStatus
    ) -> None:
        self.__base = base
        self.__node_path: NodePath = base.aspect2d.attachNewNode("TankResultUI")

        if team_type is TeamType.ALPHA:
            x = -1.2
        elif team_type is TeamType.BRAVO:
            x = 1.2
        else:
            raise ValueError(f"Invalid team_type: {team_type}")

        self.__node_path.setPos(x, 0, 0.4)
        team_setting = graphics_setting.get_team(team_type)
        team_color = team_setting.paint_color.float_rgb

        area_word = graphics_setting.get_text(HUDTextKey.PAINT_LABEL)
        area = round(tank_status.area_painted / 100.0, 1)
        area_letter = f"{area_word}{area}m²"

        kill_word = graphics_setting.get_text(HUDTextKey.ELIMS_LABEL)
        kill_letter = f"{kill_word}{tank_status.kill_count}"

        death_word = graphics_setting.get_text(HUDTextKey.DEATHS_LABEL)
        death_letter = f"{death_word}{tank_status.death_count}"

        special_word = graphics_setting.get_text(HUDTextKey.SPECIALS_LABEL)
        special_letter = f"{special_word}{tank_status.special_count}"

        DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-0.52, 0.52, -0.32, 0.37),
            pos=(0, 0, 0),
            parent=self.__node_path,
        )
        DirectFrame(
            frameColor=team_color + (1.0,),
            frameSize=(-0.5, 0.5, -0.3, 0.35),
            pos=(0, 0, 0),
            parent=self.__node_path,
        )

        font = self.__base.resource_context.font.noto_mono
        OnscreenText(
            text=area_letter,
            pos=(0, 0.225),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=font,
            parent=self.__node_path,
            sort=10,
        )
        OnscreenText(
            text=kill_letter,
            pos=(0, 0.075),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=font,
            parent=self.__node_path,
            sort=10,
        )
        OnscreenText(
            text=death_letter,
            pos=(0, -0.075),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=font,
            parent=self.__node_path,
            sort=10,
        )
        OnscreenText(
            text=special_letter,
            pos=(0, -0.225),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=font,
            parent=self.__node_path,
            sort=10,
        )


class Clash:
    """放射状のクラッシュライン演出。"""

    def __init__(self, base: MyApp, winner_team_type: TeamType) -> None:
        self.__base = base
        self.__winner_team_type = winner_team_type
        self.__particle_list: list[ParticleClash] = []
        for i in range(8):
            degree = i * 45.0 + fx_randomizer.uniform(-15.0, 15.0)
            particle = ParticleClash(self.__base, degree, self.__winner_team_type)
            self.__particle_list.append(particle)

    def update(self, result_time: float) -> None:
        for particle in self.__particle_list:
            particle.update(result_time)


class ParticleClash:
    """個別のクラッシュライン。"""

    def __init__(
        self, base: MyApp, degree: float, winner_team_type: TeamType
    ) -> None:
        self.__base = base
        self.__spawn_time = 4.0
        self.__pos = Point3(0, 0, 0)
        self.__degree = degree

        team_setting = graphics_setting.get_team(winner_team_type)
        color = team_setting.paint_color_light.float_rgb

        self.__node_path: NodePath = base.aspect2d.attachNewNode("ParticleClash")
        self.__frame = DirectFrame(
            frameColor=color + (1.0,),
            frameSize=(-0.0, 0.0, -0.1, 0.1),
            pos=(0, 0, 0),
            parent=self.__node_path,
        )
        self.__node_path.setPos(self.__pos)
        self.__node_path.setHpr(0, 0, degree)

        self.__min_length = 0.0
        self.__max_length = 2.0
        self.__stretch_duration = 0.25
        self.__shrink_duration = 0.25

    def update(self, result_time: float) -> None:
        elapsed = result_time - self.__spawn_time
        if elapsed < 0.0:
            return

        if elapsed < self.__stretch_duration:
            t = elapsed / self.__stretch_duration
            length = self.__min_length + (self.__max_length - self.__min_length) * t
            self.__frame["frameSize"] = (-0.0, length, -0.1, 0.1)
        elif elapsed < (self.__stretch_duration + self.__shrink_duration):
            shrink_elapsed = elapsed - self.__stretch_duration
            t = shrink_elapsed / self.__shrink_duration
            length = self.__min_length + (self.__max_length - self.__min_length) * t
            self.__frame["frameSize"] = (length, self.__max_length, -0.1, 0.1)
        else:
            self.destroy()

    def destroy(self) -> None:
        self.__node_path.removeNode()


class Confetti:
    """紙吹雪パーティクル生成マネージャ。"""

    def __init__(self, base: MyApp, winner_team_type: TeamType) -> None:
        self.__base = base
        self.__winner_team_type = winner_team_type
        self.__per_second = 8
        self.__start_delay = 4.0
        self.__generated_count = 0

    def update(self, result_time: float) -> None:
        if result_time < self.__start_delay:
            return
        elapsed_time = result_time - self.__start_delay
        target_count = int(elapsed_time * self.__per_second)
        spawn_count = target_count - self.__generated_count
        for _ in range(spawn_count):
            ParticleConfetti(self.__base, self.__winner_team_type)
        self.__generated_count = target_count


class ParticleConfetti:
    """舞い落ちる紙吹雪パーティクル。"""

    def __init__(self, base: MyApp, winner_team_type: TeamType) -> None:
        self.__base = base
        self.__winner_team_type = winner_team_type
        team_setting = graphics_setting.get_team(winner_team_type)
        color = team_setting.paint_color_light.float_rgb

        self.__node_path: NodePath = base.aspect2d.attachNewNode("ParticleConfetti")
        DirectFrame(
            frameColor=color + (1.0,),
            frameSize=(-0.05, 0.05, -0.05, 0.05),
            pos=(0, 0, 0),
            parent=self.__node_path,
        )
        self.__node_path.setBin("fixed", 0)
        self.__node_path.setDepthTest(False)
        self.__node_path.setDepthWrite(False)

        self.__fall_speed = fx_randomizer.uniform(0.5, 1.0)
        self.__swing_amplitude = fx_randomizer.uniform(0.0, 0.5)
        self.__swing_speed = fx_randomizer.uniform(0.0, 5.0)
        self.__rotate_speed = fx_randomizer.uniform(0.0, 180.0)

        self.__start_x = fx_randomizer.uniform(-1.7, 1.7)
        self.__node_path.setPos(self.__start_x, 0, 1.2)

        self.__task_name = f"confetti_{id(self)}"
        self.__base.taskMgr.add(self.__update, self.__task_name)

    def __update(self, task: Task.Task) -> int:
        dt = globalClock.getDt()
        t = task.time

        pos = self.__node_path.getPos()
        pos.z -= self.__fall_speed * dt
        pos.x = self.__start_x + math.sin(t * self.__swing_speed) * self.__swing_amplitude
        self.__node_path.setPos(pos)

        h, p, r = self.__node_path.getHpr()
        h += self.__rotate_speed * dt
        r += self.__rotate_speed * 0.5 * dt
        self.__node_path.setHpr(h, p, r)

        if pos.z < -1.2:
            self.__node_path.removeNode()
            return Task.done

        return Task.cont
