"""試合全体のライフサイクル・物理ワールド・HUD統括モジュール。"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
# pyrefly: ignore [missing-import]
from panda3d.bullet import BulletWorld
# pyrefly: ignore [missing-import]
from panda3d.core import Vec3

from paint_battle_custom_tank.core.collision_data import (
    CollisionGroup,
    ContactEventManager,
)
from paint_battle_custom_tank.core.setting import TeamType, battle_setting
from paint_battle_custom_tank.core.stage import ElectricCountry, Stage
from paint_battle_custom_tank.core.team import Team
from paint_battle_custom_tank.graphics.hud import BattleHUD
from paint_battle_custom_tank.graphics.hud_ending import (
    BattleFinishUI,
    BattleResultHUD,
)
from paint_battle_custom_tank.graphics.hud_starting import BattleReadyGoUI
from paint_battle_custom_tank.shared.util.yamane_state_machine import (
    StateContext,
    StateMachine,
)

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


@dataclass
class BattleStatus:
    """試合の進行時間および勝敗ステータス。"""

    start_match_time: float = 0.0
    match_time: float = 0.0
    game_time: float = 0.0
    winner_team_type: Optional[TeamType] = None


class Battle:
    """試合全体の進行ステートマシン・物理ワールド・UIを統括するクラス。"""

    def __init__(self, base: MyApp) -> None:
        self.__base = base

        # Bullet物理ワールドの初期化
        self.__physics_world = BulletWorld()
        self.__physics_world.setGravity(Vec3(0, 0, 0))
        self.__setup_collision_flags()

        # 衝突イベントマネージャー
        #self.__contact_event_manager = ContactEventManager(self.__physics_world)

        self.__team_dict: dict[TeamType, Team] = {}
        self.__stage: Optional[Stage] = None
        self.__status = BattleStatus()

        self.__hud: Optional[BattleHUD] = None
        self.__presentation_hud: Optional[BattleReadyGoUI] = None
        self.__finish_hud: Optional[BattleFinishUI] = None
        self.__result_ui: Optional[BattleResultHUD] = None

        self.__state_machine = StateMachine(self)
        self.__state_machine.set_next_state(self.__prepare)

        self.__base.accept("g", self.__accept_battle_start)

    def __setup_collision_flags(self) -> None:
        """物理コリジョングループ間の衝突有効・無効フラグを設定する。"""
        pw = self.__physics_world
        # 同チーム・同種別の衝突無効化
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_BULLET, CollisionGroup.ALPHA_BULLET, False)
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_BULLET, CollisionGroup.ALPHA_TANK, False)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_BULLET, CollisionGroup.BRAVO_BULLET, False)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_BULLET, CollisionGroup.BRAVO_TANK, False)
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_BULLET, CollisionGroup.BRAVO_BULLET, False)
        pw.setGroupCollisionFlag(CollisionGroup.WALL, CollisionGroup.WALL, False)

        # 障害物・敵対衝突の有効化
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_BULLET, CollisionGroup.WALL, True)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_BULLET, CollisionGroup.WALL, True)
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_TANK, CollisionGroup.WALL, True)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_TANK, CollisionGroup.WALL, True)
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_TANK, CollisionGroup.BRAVO_TANK, True)
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_BULLET, CollisionGroup.BRAVO_TANK, True)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_BULLET, CollisionGroup.ALPHA_TANK, True)

        # EMP電磁波の衝突有効化
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_TANK, True)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_EMP, CollisionGroup.ALPHA_TANK, True)
        pw.setGroupCollisionFlag(CollisionGroup.ALPHA_EMP, CollisionGroup.BRAVO_BULLET, True)
        pw.setGroupCollisionFlag(CollisionGroup.BRAVO_EMP, CollisionGroup.ALPHA_BULLET, True)

    def __accept_battle_start(self) -> None:
        self.__state_machine.set_next_state(self.__count_down)

    @property
    def physics_world(self) -> BulletWorld:
        return self.__physics_world

    @property
    def team_dict(self) -> dict[TeamType, Team]:
        return self.__team_dict

    @property
    def stage(self) -> Stage:
        if self.__stage is None:
            raise RuntimeError("Stage is not initialized yet.")
        return self.__stage

    @property
    def status(self) -> BattleStatus:
        return self.__status

    def __process_contacts(self) -> None:
        """doPhysics 直後に呼び出して衝突コールバックを即時・同期実行する"""
        # BulletWorld から直接すべての接触マニホールドを取得
        manifolds = self.__physics_world.get_manifolds()
        
        for manifold in manifolds:
            # 実際に接触点（Point）が存在するかチェック
            if manifold.get_num_manifold_points() > 0:
                node0 = manifold.getNode0()
                node1 = manifold.getNode1()

                # PythonTag からコールバックを取得して実行
                cb0 = node0.getPythonTag("on_contact")
                cb1 = node1.getPythonTag("on_contact")

                if cb0:
                    cb0(node1)
                if cb1:
                    cb1(node0)

    def __create_objects(self) -> None:
        self.__stage = ElectricCountry(self.__base, self)
        self.__team_dict[TeamType.ALPHA] = Team(self.__base, self, TeamType.ALPHA)
        self.__team_dict[TeamType.BRAVO] = Team(self.__base, self, TeamType.BRAVO)
        self.__hud = BattleHUD(self.__base, self)
        self.__hud.update(0, battle_setting.game_duration)
        self.__presentation_hud = BattleReadyGoUI(self.__base)
        self.__finish_hud = BattleFinishUI(self.__base)

    # ------------------------------------------------------------------
    # 物理ステップ更新の共通処理
    # ------------------------------------------------------------------
    def __update_physics(self, current_raw_time: float, dt: float) -> None:
        """物理世界および関連オブジェクト（ステージ・チーム・弾）の同期更新を行う"""
        # ステージ用の時間は game_duration（試合上限時間）を超えないようにガードする
        stage_game_time = min(self.__status.game_time, battle_setting.game_duration)

        self.stage.pre_physics_update(stage_game_time)
        for team in self.__team_dict.values():
            team.pre_physics_update(current_raw_time, dt)

        self.__physics_world.doPhysics(dt, 1, dt)
        self.__process_contacts()

        for team in self.__team_dict.values():
            team.post_physics_update(current_raw_time, dt)
        self.stage.post_physics_update(stage_game_time)

    def update(self, current_raw_time: float, dt: float) -> None:
        """毎フレームのバトル全体更新。"""
        self.__state_machine.update(current_raw_time, dt)

    # ------------------------------------------------------------------
    # 各ステート処理
    # ------------------------------------------------------------------
    def __prepare(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__create_objects()

    def __count_down(self, ctx: StateContext) -> None:
        if ctx.is_first:
            self.__status.start_match_time = ctx.current_raw_time
        self.__status.match_time = ctx.current_raw_time - self.__status.start_match_time
        if self.__presentation_hud:
            self.__presentation_hud.update(self.__status.match_time)

        if self.__status.match_time >= battle_setting.pre_game_duration:
            overflow = self.__status.match_time - battle_setting.pre_game_duration
            self.__state_machine.set_next_state(self.__battle, overflow)

    def __battle(self, ctx: StateContext) -> None:
        self.__status.match_time = ctx.current_raw_time - self.__status.start_match_time
        self.__status.game_time = (
            self.__status.match_time - battle_setting.pre_game_duration
        )
        remaining_time = battle_setting.game_duration - self.__status.game_time

        # 物理・オブジェクト更新
        self.__update_physics(ctx.current_raw_time, ctx.dt)

        if self.__presentation_hud:
            self.__presentation_hud.update(self.__status.match_time)
        if self.__hud:
            self.__hud.update(self.__status.game_time, remaining_time)

        if remaining_time <= 0:
            self.__state_machine.set_next_state(self.__battle_finish, remaining_time)

    def __battle_finish(self, ctx: StateContext) -> None:
        self.__status.match_time = ctx.current_raw_time - self.__status.start_match_time
        after_game_time = self.__status.match_time - (
            battle_setting.pre_game_duration + battle_setting.game_duration
        )
        
        if ctx.is_first:
            # 1. 試合終了時に全チームの新規射撃・操作入力をオフにする
            for team in self.__team_dict.values():
                team.disable_input()  # 戦車側の射撃フラグなどを落とす
                
            if self.__finish_hud:
                self.__finish_hud.start()

        if not ctx.is_first:
            # 試合終了後も弾の移動・着弾・爆発物理をそのまま進行させる
            self.__update_physics(ctx.current_raw_time, ctx.dt)

        if self.__finish_hud:
            self.__finish_hud.update(after_game_time)

        finish_duration = 3.0
        if after_game_time >= finish_duration:
            overflow = after_game_time - finish_duration
            self.__state_machine.set_next_state(self.__finish_fade_out, overflow)

    def __finish_fade_out(self, ctx: StateContext) -> None:
        self.__status.match_time = ctx.current_raw_time - self.__status.start_match_time
        finish_duration = 3.0
        fade_out_time = (
            self.__status.match_time
            - (
                battle_setting.pre_game_duration
                + battle_setting.game_duration
                + finish_duration
            )
        )
        fade_duration = 1.0

        if ctx.is_first:
            self.__base.transitions.fadeOut(fade_duration)

        if not ctx.is_first:
            # フェードアウト中も後ろでそのまま物理世界を動かす
            self.__update_physics(ctx.current_raw_time, ctx.dt)

        if fade_out_time >= fade_duration:
            self.__state_machine.set_next_state(self.__result)

    def __result(self, ctx: StateContext) -> None:
        self.__status.match_time = ctx.current_raw_time - self.__status.start_match_time
        finish_duration = 3.0
        fade_duration = 1.0
        result_time = self.__status.match_time - (
            battle_setting.pre_game_duration
            + battle_setting.game_duration
            + finish_duration
            + fade_duration
        )

        if ctx.is_first:
            if self.__hud:
                self.__hud.destroy()
            if self.__finish_hud:
                self.__finish_hud.destroy()
            
            # 1. 勝敗判定
            if self.stage.paint_stage.status.alpha_pixel_number >= self.stage.paint_stage.status.bravo_pixel_number:
                self.__status.winner_team_type = TeamType.ALPHA
            else:
                self.__status.winner_team_type = TeamType.BRAVO

            # 2. フェードイン
            self.__base.transitions.fadeIn(1.0)

            # 3. カメラ設定
            self.__base.camera.setPos(0, -20, 1300)
            self.__base.camera.setHpr(0, -90, 0)

            # 4. リザルトUIの生成
            self.__result_ui = BattleResultHUD(self.__base, self)

        if self.__result_ui:
            self.__result_ui.update(result_time)
