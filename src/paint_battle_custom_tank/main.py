"""ゲームアプリケーションのメインエントリーポイントモジュール。

ShowBaseを継承したメインアプリケーションクラス MyApp を定義し、
ウィンドウ、カメラ、ポストプロセスシェーダー、リソース管理、および
コアシステム（ゲームループ）の初期化と実行を行います。
"""
from __future__ import annotations

import logging
import os
import sys
from ctypes import windll

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
# pyrefly: ignore [missing-import]
from panda3d.core import (
    ClockObject,
    FrameBufferProperties,
    NodePath,
    PandaSystem,
    Shader,
    Texture,
    WindowProperties,
    loadPrcFileData,
    PStatClient, 
    ConfigVariableBool
)

globalClock = ClockObject.getGlobalClock()
import simplepbr

# Panda3Dの設定文字列をロード
loadPrcFileData(
    "",
    """
textures-power-2 None
bullet-filter-algorithm groups-mask
bullet-enable-contact-events true
""",
)

# プロジェクトのルートディレクトリ（基準パス）を sys.path に追加
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from paint_battle_custom_tank.core.core_system import CoreSystem
from paint_battle_custom_tank.graphics.resource_context import ResourceContext
from paint_battle_custom_tank.shared.util.path_manager import PathManager

logger = logging.getLogger(__name__)


class MyApp(ShowBase):
    """メインアプリケーションクラス。Panda3D ShowBase を継承しゲーム全体のライフサイクルを管理します。"""

    def __init__(self, is_debug: bool = False) -> None:
        """ShowBase、PBRパイプライン、カラーグレーディング、カメラ、リソース、コアシステムを初期化します。

        Args:
            is_debug: デバッグモード（フレームレート表示や座標軸モデル表示）の有効/無効フラグ
        """
        super().__init__()

        if self.loader is None:
            return

        # PBR パイプラインとカラーグレーディングのセットアップ
        self.__setup_pbr_and_color_grading()

        # ウィンドウプロパティとデバッグ用設定
        self.__setup_window(is_debug=is_debug)

        # カメラの位置・角度・FOV設定
        self.__setup_camera()

        # キーバインド設定
        self.accept("space", self.oobe)
        self.accept("q", self.debug_analyze)
        self.accept("s", self.debug_screenshot)
        self.disableMouse()

        # リソースコンテキストとコアシステムの初期化
        self.__resource_context: ResourceContext = ResourceContext(self)
        self.__core_system: CoreSystem = CoreSystem(self)

        # メインループタスクの登録
        self.taskMgr.add(self.__update, "update_master")

    @property
    def resource_context(self) -> ResourceContext:
        """共通リソースコンテキストを取得します。"""
        return self.__resource_context

    def __setup_pbr_and_color_grading(self) -> None:
        """simplepbr および GLSL シェーダーによるカラーグレーディングを初期化します。"""
        pipeline = simplepbr.init(exposure=0, use_normal_maps=True)
        self.manager = pipeline._filtermgr

        fbprops = FrameBufferProperties()
        fbprops.setFloatColor(True)  # 16bit float

        colortex = Texture()
        self.quad = self.manager.renderSceneInto(colortex=colortex, fbprops=fbprops)
        if self.quad is not None:
            shader = Shader.load(
                Shader.SLGLSL,
                PathManager.resource_vfs("shaders/color_grading_v.glsl"),
                PathManager.resource_vfs("shaders/color_grading_f.glsl"),
            )
            self.quad.setShader(shader)
            self.quad.setShaderInput("colortex", colortex)

    def __setup_window(self, is_debug: bool) -> None:
        """ウィンドウサイズ、タイトル、デバッグ軸モデルを設定します。

        Args:
            is_debug: デバッグ表示フラグ
        """
        self.properties = WindowProperties()
        self.properties.setTitle("Gently Radiant Paint Battle")

        self.axis: NodePath = self.loader.loadModel("models/zup-axis")
        self.axis.setPos(0, 0, 0)
        self.axis.setScale((1, 1, 1))

        if is_debug:
            self.properties.setSize(1280, 720)
            self.setFrameRateMeter(True)
            self.setSceneGraphAnalyzerMeter(True)
            self.axis.reparentTo(self.render)
        else:
            self.properties.setSize(1280, 720)

        self.properties.setFixedSize(True)
        if self.win is not None:
            self.win.requestProperties(self.properties)

    def __setup_camera(self) -> None:
        """トップダウン視点のカメラクリップ距離、FOV、位置、回転角を設定します。"""
        lens = self.camLens
        lens.setNear(2.0)
        lens.setFar(2000.0)
        lens.setFov(20.0)
        self.camera.setPos(0, -220, 1400)
        self.camera.setHpr(0, -80, 0)

    def debug_screenshot(self) -> None:
        """デバッグ用のスクリーンショットを出力します。"""
        self.movie(namePrefix="image", duration=1, fps=1, format="png")
        logger.info("Screenshot taken")

    def debug_analyze(self) -> None:
        """シングラフの構造・頂点数をコンソールに解析出力します。"""
        self.render.analyze()

    def __update(self, task: Task.Task) -> int:
        """毎フレーム呼び出されるメインループタスク。

        Args:
            task: Panda3Dタスクインスタンス

        Returns:
            タスク継続フラグ (Task.cont)
        """
        current_raw_time = globalClock.getFrameTime()
        dt = globalClock.getDt()
        self.__core_system.update(current_raw_time, dt)
        return task.cont


def main() -> None:
    """メイン実行関数。高精度タイマー設定、FPS上限設定、およびアプリケーションの起動を行います。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    print(f"Current Directory: {os.getcwd()}")
    print(f"sys.path[0]: {sys.path[0]}")
    print(f"sys.path: {sys.path}")
    print(f"Python Version: {sys.version}")
    print(f"Panda3D Version: {PandaSystem.getVersionString()}")

    # Windows タイマー精度を 1ms に設定
    windll.winmm.timeBeginPeriod(1)
    try:
        #PStatClient.connect()
        #ConfigVariableBool("bullet-pstats", True).setValue(True)
        globalClock.setMode(ClockObject.M_limited)
        globalClock.setFrameRate(24)
        app = MyApp()
        app.run()
    finally:
        windll.winmm.timeEndPeriod(1)
        logger.info("Application terminated cleanly.")


if __name__ == "__main__":
    main()