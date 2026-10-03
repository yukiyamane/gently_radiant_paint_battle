"""HUD（ヘッドレスアップディスプレイ）およびゲーム内UIコンポーネントモジュール。

タイマー、塗り面積ゲージ、各チーム/戦車のHP・SPステータス、カウントダウン演出などのUI表示を管理します。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
# pyrefly: ignore [missing-import]
from panda3d.core import NodePath, TextNode, TransparencyAttrib

from paint_battle_custom_tank.core.main_weapon_setting import WeaponSettingFactory
from paint_battle_custom_tank.core.setting import TeamSetting, TeamType, battle_setting, tank_setting
from paint_battle_custom_tank.core.tank_status import TankCondition
from paint_battle_custom_tank.core.special_weapon_setting import SpecialWeaponSettingFactory
from paint_battle_custom_tank.graphics.setting import HUDTextKey, graphics_setting, Language
from paint_battle_custom_tank.graphics.material import ColorStorage
from paint_battle_custom_tank.shared.util.path_manager import PathManager
from paint_battle_custom_tank.shared.util.randomizer import fx_randomizer

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import TankStatus
    from paint_battle_custom_tank.core.team import Team
    from paint_battle_custom_tank.main import MyApp


class BattleHUD:
    """バトル全体のHUD（枠、タイマー、塗り面積、チームステータス、カウントダウン）を統括するクラス。"""

    def __init__(self, base: MyApp, battle: Battle) -> None:
        """BattleHUDを初期化し、子UIノードを構築します。

        Args:
            base: ShowBase / MyApp インスタンス
            battle: バトルロジック管理インスタンス
        """
        self.__base: MyApp = base
        self.__battle: Battle = battle
        self.__node_path: NodePath = self.__base.aspect2d.attachNewNode("BattleHUD")

        self.__border = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-2.0, 2.0, -0.2, 0.2),
            pos=(0, 0, 0.8),
            parent=self.__node_path,
        )

        self.__border_left = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-0.2, 0.2, -1.0, 1.0),
            pos=(-1.7, 0, 0.0),
            parent=self.__node_path,
        )
        self.__border_right = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-0.2, 0.2, -1.0, 1.0),
            pos=(1.7, 0, 0.0),
            parent=self.__node_path,
        )

        self.__game_timer_ui = GameTimerUI(base)
        self.__paint_coverage_ui = PaintCoverageUI(base, battle)
        self.__team_status_ui_dict: dict[TeamType, TeamStatusUI] = {
            TeamType.ALPHA: TeamStatusUI(base, TeamType.ALPHA),
            TeamType.BRAVO: TeamStatusUI(base, TeamType.BRAVO),
        }
        self.__battle_count_down_ui = BattleCountDownUI(base)

    def destroy(self) -> None:
        """全HUDリソースおよび子UIを破棄します。"""
        self.__node_path.removeNode()
        self.__game_timer_ui.destroy()
        self.__paint_coverage_ui.destroy()
        for status_ui in self.__team_status_ui_dict.values():
            status_ui.destroy()

    def update(self, game_time: float, remaining_time: float) -> None:
        """HUDの全表示内容を最新のバトル状態で更新します。

        Args:
            game_time: 試合経過時間（秒）
            remaining_time: 残り試合時間（秒）
        """
        self.__game_timer_ui.update(remaining_time)
        self.__paint_coverage_ui.update(remaining_time)
        for team_type, status_ui in self.__team_status_ui_dict.items():
            status_ui.update(self.__battle.team_dict[team_type])
        self.__battle_count_down_ui.update(game_time, remaining_time)


class GameTimerUI:
    """残り試合時間を MM:SS 形式で画面上部に表示するUIクラス。"""

    def __init__(self, base: MyApp) -> None:
        """タイマーUIを生成します。

        Args:
            base: ShowBase / MyApp インスタンス
        """
        self.__base: MyApp = base
        self.__node_path: NodePath = self.__base.aspect2d.attachNewNode("GameTimerUI")
        self.__text = OnscreenText(
            text="3:00",
            pos=(0, 0.8),
            scale=0.15,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
        )

    def update(self, remaining_time: float) -> None:
        """残り時間表示を更新します。

        Args:
            remaining_time: 残り秒数
        """
        second = math.ceil(remaining_time)
        minute = second // 60
        second = second % 60
        self.__text.setText(f"{minute}:{second:02d}")

    def destroy(self) -> None:
        """タイマーノードを破棄します。"""
        self.__node_path.removeNode()


class PaintCoverageUI:
    """両チームの塗り面積比率をバーとパーセンテージで表示するUIクラス。"""

    def __init__(self, base: MyApp, battle: Battle) -> None:
        """塗り面積UIを生成します。

        Args:
            base: ShowBase / MyApp インスタンス
            battle: バトルインスタンス
        """
        self.__base: MyApp = base
        self.__battle: Battle = battle
        self.__node_path: NodePath = self.__base.aspect2d.attachNewNode("PaintCoverageUI")

        z = 0.65

        alpha_team_setting = graphics_setting.get_team(TeamType.ALPHA)
        bravo_team_setting = graphics_setting.get_team(TeamType.BRAVO)

        alpha_color = alpha_team_setting.paint_color.float_rgb
        bravo_color = bravo_team_setting.paint_color.float_rgb

        alpha_text_color = alpha_team_setting.paint_color.float_rgb
        bravo_text_color = bravo_team_setting.paint_color.float_rgb

        self.__frame_back = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-1.7, 1.7, -0.05, 0.05),
            pos=(0, 0, z),
            parent=self.__node_path,
        )
        self.__alpha_bar = DirectFrame(
            frameColor=alpha_color + (1.0,),
            frameSize=(-1.44, -1.44, -0.04, 0.04),
            pos=(0, 0, z),
            parent=self.__node_path,
        )
        self.__alpha_text = OnscreenText(
            text="0.0%",
            pos=(-1.465, z - 0.03),
            scale=0.09,
            fg=alpha_text_color + (1.0,),
            align=TextNode.ARight,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )

        self.__bravo_bar = DirectFrame(
            frameColor=bravo_color + (1.0,),
            frameSize=(1.44, 1.44, -0.04, 0.04),
            pos=(0, 0, z),
            parent=self.__node_path,
        )
        self.__bravo_text = OnscreenText(
            text="0.0%",
            pos=(1.68, z - 0.03),
            scale=0.09,
            fg=bravo_text_color + (1.0,),
            align=TextNode.ARight,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )

        self.__frame_hide = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-1.45, 1.45, -0.00, 0.00),
            pos=(0, 0, z),
            parent=self.__node_path,
        )

        self.__is_text_question: bool = False

    def update(self, remaining_time: float) -> None:
        """塗り面積比率と隠蔽アニメーションを更新します。

        Args:
            remaining_time: 残り試合時間（秒）
            paint_coverage_dict: チームごとの塗り面積比率辞書 (0.0〜1.0)
        """
        alpha_ratio = self.__battle.stage.paint_stage.status.alpha_ratio
        alpha_percentage = round(alpha_ratio * 100, 1)

        bravo_ratio = self.__battle.stage.paint_stage.status.bravo_ratio
        bravo_percentage = round(bravo_ratio * 100, 1)

        if 8 < remaining_time:
            self.__alpha_text.setText(f"{alpha_percentage}%")
            self.__bravo_text.setText(f"{bravo_percentage}%")

        self.__alpha_bar["frameSize"] = (-1.44, -1.44 + (1.44 * 2) * alpha_ratio, -0.04, 0.04)
        self.__bravo_bar["frameSize"] = (1.44 - (1.44 * 2) * bravo_ratio, 1.44, -0.04, 0.04)

        if remaining_time <= 10:
            # 10 から 8 に減るにつれて、t が 0 から 1 に増える
            t = min(1.0, (10.0 - remaining_time) / 2.0)
            bottom = 0.04 + -0.08 * t
            self.__frame_hide["frameSize"] = (-1.45, 1.45, bottom, 0.04)

        if remaining_time <= 8 and not self.__is_text_question:
            self.__alpha_text.setText("??.?%")
            self.__bravo_text.setText("??.?%")
            self.__is_text_question = True

    def destroy(self) -> None:
        """UIノードを破棄します。"""
        self.__node_path.removeNode()


class TeamStatusUI:
    """チーム全体のステータス表示を管理するラッパークラス。"""

    def __init__(self, base: MyApp, team_type: TeamType) -> None:
        """TeamStatusUIを生成します。

        Args:
            base: ShowBase / MyApp インスタンス
            team_type: 対象チームタイプ
        """
        self.__tank_status_ui = TankStatusUI(base, team_type)

    def update(self, team: Team) -> None:
        """チームに所属する戦車のステータスを更新します。

        Args:
            team: 対象チームインスタンス
        """
        for tank in team.tank_list:
            self.__tank_status_ui.update(tank.status)

    def destroy(self) -> None:
        """ステータスUIを破棄します。"""
        self.__tank_status_ui.destroy()


class TankStatusUI:
    """戦車のHPバー、SPバー、各種武装アイコン・名称を表示するUIクラス。"""

    def __init__(self, base: MyApp, team_type: TeamType) -> None:
        """TankStatusUIを生成し、HP/SPバーと武器アイコン・ラベルを構築します。

        Args:
            base: ShowBase / MyApp インスタンス
            team_type: 対象チームタイプ
        """
        self.__base: MyApp = base
        self.__node_path: NodePath = self.__base.aspect2d.attachNewNode("TankStatusUI")

        team_setting = TeamSetting.get(team_type)
        main_weapon_setting = WeaponSettingFactory.main(team_setting.tank_main_weapon_type)
        sub_weapon_setting = WeaponSettingFactory.sub(team_setting.tank_sub_weapon_type)
        special_weapon_setting = SpecialWeaponSettingFactory.create(
            team_setting.tank_special_weapon_type
        )

        color = graphics_setting.get_team(team_type).paint_color.float_rgb

        x = -1.65 if team_type == TeamType.ALPHA else 1.65

        self.__bar_width: float = 0.2
        self.__bar_height: float = 0.5
        self.__bar_content_padding: float = 0.01

        self.__hp_bar_back = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(
                -self.__bar_width / 2,
                self.__bar_width / 2,
                -self.__bar_height / 2,
                self.__bar_height / 2,
            ),
            pos=(x, 0, 0.25),
            parent=self.__node_path,
        )
        self.__hp_bar_front = DirectFrame(
            frameColor=ColorStorage.vivid_green.float_rgb + (1, ),
            frameSize=(
                -(self.__bar_width / 2 - self.__bar_content_padding),
                self.__bar_width / 2 - self.__bar_content_padding,
                -(self.__bar_height / 2 - self.__bar_content_padding) + 0.1,
                self.__bar_height / 2 - self.__bar_content_padding,
            ),
            pos=(x, 0, 0.25),
            parent=self.__node_path,
        )

        self.__hp_text = OnscreenText(
            text="HP",
            pos=(x, -0.1),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )
        self.__hp_amount_text = OnscreenText(
            text="100",
            pos=(x, 0.025),
            scale=0.1,
            fg=ColorStorage.vivid_green.float_rgb + (1, ),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )

        self.__sp_bar_back = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(
                -self.__bar_width / 2,
                self.__bar_width / 2,
                -self.__bar_height / 2,
                self.__bar_height / 2,
            ),
            pos=(x, 0, -0.5),
            parent=self.__node_path,
        )
        self.__sp_bar_front = DirectFrame(
            frameColor=color + (1.0,),
            frameSize=(
                -(self.__bar_width / 2 - self.__bar_content_padding),
                self.__bar_width / 2 - self.__bar_content_padding,
                -(self.__bar_height / 2 - self.__bar_content_padding) + 0.1,
                self.__bar_height / 2 - self.__bar_content_padding,
            ),
            pos=(x, 0, -0.5),
            parent=self.__node_path,
        )
        self.__sp_text = OnscreenText(
            text="SP",
            pos=(x, -0.85),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )
        self.__sp_amount_text = OnscreenText(
            text="100",
            pos=(x, -0.725),
            scale=0.1,
            fg=color + (1,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.noto_mono,
            parent=self.__node_path,
            sort=10,
        )

        # 主砲UI
        main_x = -0.475 if team_type == TeamType.ALPHA else 0.475
        self.__main_weapon_frame = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-0.225, 0.225, -0.13, 0.13),
            pos=(main_x, 0, 0.85),
            parent=self.__node_path,
        )
        self.__main_weapon_icon = OnscreenImage(
            image=PathManager.resource_vfs(f"textures/hud/{main_weapon_setting.image_file_name}.png"),
            pos=(main_x + 0.1, 0, 0.82),
            parent=self.__node_path,
            scale=0.08,
            color=color + (1.0,),
        )
        self.__main_weapon_icon.setTransparency(TransparencyAttrib.MAlpha)

        self.__main_weapon_type_name_label = OnscreenText(
            text=graphics_setting.get_text(HUDTextKey.MAIN_WEAPON_PREFIX),
            pos=(main_x - 0.1, 0.8),
            scale=0.05,
            fg=color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )
        main_text = main_weapon_setting.name_dict[graphics_setting.language]
        self.__main_weapon_text = OnscreenText(
            text=main_text,
            pos=(main_x, 0.92),
            scale=0.05,
            fg=color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )

        # 副砲UI
        sub_x = -0.975 if team_type == TeamType.ALPHA else 0.975
        self.__sub_weapon_frame = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-0.225, 0.225, -0.13, 0.13),
            pos=(sub_x, 0, 0.85),
            parent=self.__node_path,
        )
        self.__sub_weapon_icon = OnscreenImage(
            image=PathManager.resource_vfs(f"textures/hud/{sub_weapon_setting.image_file_name}.png"),
            pos=(sub_x + 0.1, 0, 0.82),
            parent=self.__node_path,
            scale=0.08,
            color=color + (1.0,),
        )
        self.__sub_weapon_icon.setTransparency(TransparencyAttrib.MAlpha)

        self.__sub_weapon_type_name_label = OnscreenText(
            text=graphics_setting.get_text(HUDTextKey.SUB_WEAPON_PREFIX),
            pos=(sub_x - 0.1, 0.8),
            scale=0.05,
            fg=color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )
        self.__sub_weapon_text = OnscreenText(
            text=sub_weapon_setting.name_dict[graphics_setting.language],
            pos=(sub_x, 0.92),
            scale=0.05,
            fg=color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )

        # 特殊砲UI
        special_x = -1.475 if team_type == TeamType.ALPHA else 1.475
        self.__special_weapon_frame = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-0.225, 0.225, -0.13, 0.13),
            pos=(special_x, 0, 0.85),
            parent=self.__node_path,
        )
        self.__special_weapon_icon = OnscreenImage(
            image=PathManager.resource_vfs(
                f"textures/hud/{special_weapon_setting.image_file_name}.png"
            ),
            pos=(special_x + 0.1, 0, 0.82),
            parent=self.__node_path,
            scale=0.08,
            color=color + (1.0,),
        )
        self.__special_weapon_icon.setTransparency(TransparencyAttrib.MAlpha)

        self.__special_weapon_type_name_label = OnscreenText(
            text=graphics_setting.get_text(HUDTextKey.SPECIAL_WEAPON_PREFIX),
            pos=(special_x - 0.1, 0.8),
            scale=0.05,
            fg=color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )
        self.__special_weapon_text = OnscreenText(
            text=special_weapon_setting.name_dict[graphics_setting.language],
            pos=(special_x, 0.92),
            scale=0.05,
            fg=color + (1.0,),
            align=TextNode.ACenter,
            font=self.__base.resource_context.font.mplus_bold,
            parent=self.__node_path,
            sort=10,
        )

    def update(self, tank_status: TankStatus) -> None:
        """戦車のHPとSP残量に応じてバーの長さとテキスト数値を更新します。

        Args:
            tank_status: 戦車のステータス情報
        """
        if tank_status.condition is TankCondition.ALIVE: 
            hp_ratio = tank_status.hp / tank_status.max_hp
        else:
            hp_ratio = tank_status.time_since_death / tank_setting.respawn_time
            #self.__hp_amount_text.setText(f"{math.ceil(hp_ratio * 100)}")
        self.__hp_amount_text.setText(f"{math.ceil(tank_status.hp / 10)}")

        hp_bottom = -((self.__bar_height) / 2 - self.__bar_content_padding) + 0.1
        hp_top = hp_bottom + ((self.__bar_height - 0.1) - 2 * self.__bar_content_padding) * hp_ratio
        self.__hp_bar_front["frameSize"] = (
            -(self.__bar_width / 2 - self.__bar_content_padding),
            self.__bar_width / 2 - self.__bar_content_padding,
            hp_bottom,
            hp_top,
        )
        if hp_ratio <= 0.2:
            color = ColorStorage.vivid_red.float_rgb
        elif hp_ratio <= 0.5:
            color = ColorStorage.strong_yellow.float_rgb
        else:
            color = ColorStorage.vivid_green.float_rgb
        self.__hp_amount_text.setFg(color + (1,))
        self.__hp_bar_front["frameColor"] = color + (1,)


        self.__sp_amount_text.setText(f"{math.ceil(tank_status.sp * 100)}")

        sp_ratio = tank_status.sp / tank_status.max_sp
        sp_bottom = -((self.__bar_height) / 2 - self.__bar_content_padding) + 0.1
        sp_top = sp_bottom + ((self.__bar_height - 0.1) - 2 * self.__bar_content_padding) * sp_ratio
        self.__sp_bar_front["frameSize"] = (
            -(self.__bar_width / 2 - self.__bar_content_padding),
            self.__bar_width / 2 - self.__bar_content_padding,
            sp_bottom,
            sp_top,
        )

    def destroy(self) -> None:
        """ステータスノードを破棄します。"""
        self.__node_path.removeNode()


class BattleCountDownUI:
    """Battle終了直前（10秒前〜）にカウントダウン（10, 9, 8...）演出を表示・管理するUIクラス。"""

    def __init__(self, base: MyApp) -> None:
        """カウントダウン管理UIを初期化します。

        Args:
            base: ShowBase / MyApp インスタンス
        """
        self.__base: MyApp = base
        self.__last_number: int | None = None
        self.__particle_list: list[ParticleCountDown] = []

    def update(self, game_time: float, remaining_time: float) -> None:
        """残り時間に応じてカウントダウン用パーティクルを生成・更新します。

        Args:
            game_time: 試合経過時間（秒）
            remaining_time: 残り試合時間（秒）
        """
        # 10〜1 のときだけカウントダウン演出を出す
        if 0 <= remaining_time <= 10:
            number = int(remaining_time) + 1
            if number != self.__last_number:
                start_time = battle_setting.game_duration - number
                particle_count_down = ParticleCountDown(self.__base, number, start_time)
                self.__particle_list.append(particle_count_down)
                self.__last_number = number

        # カウントダウン用パーティクルを更新
        for particle in self.__particle_list:
            particle.update(game_time)

        # 完了したパーティクルを削除
        self.__particle_list = [p for p in self.__particle_list if not p.is_finished]


class ParticleCountDown:
    """カウントダウンの各数字パーティクル演出（回転・フェードアウト）を処理するクラス。"""

    def __init__(self, base: MyApp, number: int, start_time: float) -> None:
        """数字パーティクルを生成し、初期位置・回転設定を施します。

        Args:
            base: ShowBase / MyApp インスタンス
            number: 表示するカウントダウン数字
            start_time: 本来の演出開始基準時刻（秒）
        """
        self.__base: MyApp = base
        self.__number: int = number
        self.__start_time: float = start_time

        self.__node_path: NodePath = self.__base.aspect2d.attachNewNode(
            f"ParticleCountDown_{number}UI"
        )
        offset_x = fx_randomizer.uniform(-0.1, 0.1)
        offset_y = fx_randomizer.uniform(-0.1, 0.1)
        self.__node_path.setPos(offset_x, 0, offset_y)

        self.__pivot: NodePath = self.__node_path.attachNewNode("pivot")
        self.__text = OnscreenText(
            text=f"{number}",
            pos=(0, 0),
            scale=1.5,
            fg=(1, 1, 1, 1),
            parent=self.__pivot,
            font=self.__base.resource_context.font.mplus_bold_hq,
        )
        self.__text.setTransparency(TransparencyAttrib.MAlpha)
        self.__text.setAlphaScale(0.7)
        self.__pivot.setZ(-0.6)

        if number % 2 == 0:
            self.__min_rot, self.__max_rot = -10.0, 10.0
        else:
            self.__min_rot, self.__max_rot = 10.0, -10.0

        self.__is_finished: bool = False

    @property
    def is_finished(self) -> bool:
        """演出が終了したかどうかを取得します。"""
        return self.__is_finished

    def update(self, game_time: float) -> None:
        """経過時間に応じた回転およびアルファフェードアニメーションを更新します。

        Args:
            game_time: 試合経過時間（秒）
        """
        elapsed = game_time - self.__start_time
        duration = 1.0
        t = min(elapsed / duration, 1.0)

        # 回転の計算
        rot = t * (self.__max_rot - self.__min_rot) + self.__min_rot
        self.__node_path.setHpr(0, 0, rot)

        # フェードアウトの計算 (0.5秒後から開始)
        start_alpha_time = 0.5
        duration_alpha = 0.5
        if start_alpha_time <= elapsed:
            t_alpha = min((elapsed - start_alpha_time) / duration_alpha, 1.0)
            v_alpha = t_alpha**2
            alpha = max(0.0, 1.0 - v_alpha) * 0.7
            self.__text.setAlphaScale(alpha)
            scale = max(0.01, 1.0 - v_alpha)
            self.__node_path.setScale(scale)

        # 終了判定
        if elapsed >= duration:
            self.__node_path.removeNode()
            self.__is_finished = True
