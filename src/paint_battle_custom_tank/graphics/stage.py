"""ステージ地形モデルおよび地面インクテクスチャ描画モジュール。"""

from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
# pyrefly: ignore [missing-import]
from panda3d.core import CardMaker, NodePath, Point3, Texture, TextureStage, VBase3, Vec3

from paint_battle_custom_tank.graphics.environment import Environment
from paint_battle_custom_tank.shared.util.path_manager import PathManager
from paint_battle_custom_tank.graphics.setting import graphics_setting

if TYPE_CHECKING:
    from paint_battle_custom_tank.main import MyApp


class StageGraphics:
    """ステージのベース地面およびライティング環境の初期化クラス。"""

    def __init__(self, base: MyApp) -> None:
        self.__base = base
        self.__ground: NodePath = (
            self.__base.resource_context.primitive_model.plane_2m.copyTo(
                self.__base.render
            )
        )
        self.__ground.setScale(500.0)
        self.__ground.setMaterial(
            self.__base.resource_context.material_storage.gray_diff
        )
        self.__environment = Environment(base)

    def update(self, dt: float) -> None:
        pass


class SlidingBoxGraphics:
    """スライド壁の3Dメッシュ描画クラス。"""

    def __init__(self, base: MyApp, radius: Vec3) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            self.__base.resource_context.primitive_model.cube_2m.copyTo(
                self.__base.render
            )
        )
        self.__node_path.setScale(radius)
        self.__node_path.setMaterial(
            self.__base.resource_context.material_storage.black_diff
        )

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)


class RotationBoxGraphics:
    """回転壁の3Dメッシュ描画クラス。"""

    def __init__(self, base: MyApp, radius: Vec3) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            self.__base.resource_context.primitive_model.cube_2m.copyTo(
                self.__base.render
            )
        )
        self.__node_path.setScale(radius)
        self.__node_path.setMaterial(
            self.__base.resource_context.material_storage.black_diff
        )

    def set_pos(self, pos: Vec3) -> None:
        self.__node_path.setPos(pos)

    def set_hpr(self, hpr: Vec3) -> None:
        self.__node_path.setHpr(hpr)


class FixedBoxGraphics:
    """固定壁の3Dメッシュ描画クラス。"""

    def __init__(self, base: MyApp, radius: VBase3) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            self.__base.resource_context.primitive_model.cube_2m.copyTo(
                self.__base.render
            )
        )
        self.__node_path.setScale(radius)
        self.__node_path.setMaterial(
            self.__base.resource_context.material_storage.black_diff
        )

    def set_pos(self, pos: Point3) -> None:
        self.__node_path.setPos(pos)

    def set_hpr(self, hpr: VBase3) -> None:
        self.__node_path.setHpr(hpr)


class KnockBackPillarGraphics:
    """ノックバック柱の3Dメッシュ描画クラス。"""

    def __init__(self, base: MyApp, radius: float, height: float) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            self.__base.resource_context.primitive_model.cylinder_2m.copyTo(
                self.__base.render
            )
        )
        self.__node_path.setScale(radius, radius, height)
        self.__node_path.setMaterial(
            self.__base.resource_context.material_storage.black_diff, 1
        )

    def set_pos(self, pos: Point3) -> None:
        self.__node_path.setPos(pos)

    def set_scale(self, scale: VBase3) -> None:
        self.__node_path.setScale(scale)


class OrbitPillarGraphics:
    """周回柱の3Dメッシュ描画クラス。"""

    def __init__(self, base: MyApp, radius: float) -> None:
        self.__base = base
        self.__node_path: NodePath = (
            self.__base.resource_context.primitive_model.cylinder_2m.copyTo(
                self.__base.render
            )
        )
        self.__node_path.setScale(radius, radius, 10.0)
        self.__node_path.setMaterial(
            self.__base.resource_context.material_storage.black_diff, 1
        )

    def set_pos(self, pos: Point3) -> None:
        self.__node_path.setPos(pos)


class PaintStageGraphics:
    """地面ポリゴンへの動的インクテクスチャ適用およびバッファ高速転送クラス。"""

    def __init__(self, base: MyApp) -> None:
        self.__base = base
        self.__width = 1024
        self.__height = 512
        self.__tex = Texture("ink_texture")
        self.__tex.setup_2d_texture(
            self.__width, self.__height, Texture.T_unsigned_byte, Texture.F_srgb
        )


        alpha_rgb = graphics_setting.alpha.paint_color.byte_rgb
        bravo_rgb = graphics_setting.bravo.paint_color.byte_rgb


        self.__palette = np.ones((256, 3), dtype=np.uint8) * 255
        self.__palette[0] = (255, 255, 255)
        self.__palette[1] = alpha_rgb[::-1]
        self.__palette[2] = bravo_rgb[::-1]

        cm = CardMaker("floor")
        cm.set_frame(-200, 200, -100, 100)
        self.__floor: NodePath = self.__base.render.attach_new_node(cm.generate())
        self.__floor.setP(-90)
        self.__floor.setPos(0, 0, 0.1)

        ts_base = TextureStage("baseColorTexture")
        ts_base.setMode(TextureStage.M_modulate)
        ts_base.set_sort(0)
        self.__floor.setTexture(ts_base, self.__tex, 1)

        init_array = np.zeros((self.__height, self.__width), dtype=np.uint8)
        self.apply_paint(init_array)

        self.__normal: Texture = self.__base.loader.loadTexture(
            PathManager.resource_vfs("textures/canvas_sheet_normal_2.png")
        )
        ts_normal = TextureStage("normalTexture")
        ts_normal.setMode(TextureStage.M_normal)
        ts_normal.set_sort(1)
        self.__floor.setTexture(ts_normal, self.__normal, 1)

    def apply_paint(self, array: np.ndarray) -> None:
        """NumPy配列からBGRテクスチャバッファを生成し、VRAMへ転送する。"""
        frame_data = self.__palette[array]
        raw_buffer = self.__tex.modify_ram_image()
        dest_view = memoryview(raw_buffer)
        dest_view[:] = frame_data.ravel()