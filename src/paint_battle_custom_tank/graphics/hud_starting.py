"""試合開始前のReady / Go!演出UIモジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import math
from direct.gui.OnscreenText import OnscreenText
# pyrefly: ignore [missing-import]
from panda3d.core import NodePath, Point3, TextNode, TransparencyAttrib

from paint_battle_custom_tank.core.setting import battle_setting
from paint_battle_custom_tank.graphics.setting import HUDTextKey, graphics_setting
from paint_battle_custom_tank.shared.util.randomizer import fx_randomizer

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


class BattleReadyGoUI:
    """試合開始前のReady, Go!テキストタイピング・拡大演出UI。"""

    def __init__(self, base: MyApp) -> None:
        self.__base = base
        self.__ready_particle: Optional[ParticleReady] = None
        self.__go_particle: Optional[ParticleGo] = None

    def update(self, match_time: float) -> None:
        pre_match_duration = battle_setting.pre_game_duration
        remaining = pre_match_duration - match_time

        # Ready演出
        if 0.0 <= match_time < pre_match_duration:
            if self.__ready_particle is None:
                self.__ready_particle = ParticleReady(self.__base, start_time=0.0)
            self.__ready_particle.update(match_time)
        elif self.__ready_particle is not None:
            self.__ready_particle.destroy()
            self.__ready_particle = None

        # Go!演出
        if remaining <= 0.0:
            if self.__go_particle is None:
                self.__go_particle = ParticleGo(
                    self.__base, start_time=pre_match_duration
                )
            self.__go_particle.update(match_time)
            if match_time >= pre_match_duration + 1.0:
                self.__go_particle.destroy()
                self.__go_particle = None

    def destroy(self) -> None:
        if self.__ready_particle:
            self.__ready_particle.destroy()
            self.__ready_particle = None
        if self.__go_particle:
            self.__go_particle.destroy()
            self.__go_particle = None


class ParticleReady:
    """Ready... テキストのタイピング表示クラス。"""

    def __init__(self, base: MyApp, start_time: float) -> None:
        self.__base = base
        self.__start_time = start_time
        self.__node_path: NodePath = base.aspect2d.attachNewNode("ParticleReadyUI")

        color = graphics_setting.alpha.paint_color.float_rgb

        self.__text = OnscreenText(
            text="",
            pos=(0, -0.2),
            scale=0.5,
            fg=color + (1.0,),
            shadow=(0, 0, 0, 1),
            shadowOffset=(0.05, 0.05),
            align=TextNode.ACenter,
            font=base.resource_context.font.mplus_bold_hq,
            parent=self.__node_path,
        )

        self.__full_text = graphics_setting.get_text(HUDTextKey.READY)
        self.__length = len(self.__full_text)

    def update(self, match_time: float) -> None:
        elapsed = match_time - self.__start_time
        duration_text = 0.5

        if elapsed <= duration_text:
            progress = max(0.0, min(1.0, elapsed / duration_text))
            current_chars = int(self.__length * progress)
            self.__text.setText(self.__full_text[:current_chars])
        else:
            self.__text.setText(self.__full_text)

    def destroy(self) -> None:
        self.__node_path.removeNode()


class ParticleGo:
    """Go! テキストの拡縮・ポップ表示クラス。"""

    def __init__(self, base: MyApp, start_time: float) -> None:
        self.__base = base
        self.__start_time = start_time
        self.__node_path: NodePath = base.aspect2d.attachNewNode("ParticleGoUI")

        full_text = graphics_setting.get_text(HUDTextKey.GO)

        color = graphics_setting.bravo.paint_color.float_rgb

        self.__text = OnscreenText(
            text=full_text,
            pos=(0, -0.3),
            scale=1,
            fg=color + (1,),
            shadow=(0, 0, 0, 1),
            shadowOffset=(0.05, 0.05),
            align=TextNode.ACenter,
            font=base.resource_context.font.mplus_bold_hq,
            parent=self.__node_path,
        )
        self.__text.setTransparency(TransparencyAttrib.MAlpha)

    def update(self, match_time: float) -> None:
        # 「現在時間 - 本来の開始時間」で経過秒数を計算（遅れが自動補正される）
        elapsed = match_time - self.__start_time

        duration = 1.0  # 演出の総時間（1秒）
        t = min(elapsed / duration, 1.0)

        # ─── 震え（減衰する揺れ）の計算 ───
        # elapsed（経過時間）を直接使うため、遅れて生成された場合は
        # 最初から「激しい揺れの山」を通り越した状態からスタートします
        shake = (1.0 / (1.0 + t * 5)) * 10  # 時間とともに減衰
        
        # 乱数のシードや発生自体は毎フレーム行いますが、最大幅（shake）が絶対時間で減衰します
        offset_x = fx_randomizer.uniform(-shake, shake) * 0.005
        offset_y = fx_randomizer.uniform(-shake, shake) * 0.005
        self.__text.setPos(offset_x, offset_y - 0.3)

        # ─── 透明度（フェードアウト）の計算 ───
        v = t ** 2
        alpha = max(0.0, 1.0 - v)
        self.__text.setAlphaScale(alpha)
        #print(alpha)

    def destroy(self) -> None:
        self.__node_path.removeNode()
