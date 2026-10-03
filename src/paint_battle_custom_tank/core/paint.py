"""ペイントブラシ処理およびマスク生成モジュール。"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import numpy as np
# pyrefly: ignore [missing-import]
from panda3d.core import Texture, Vec3
from paint_battle_custom_tank.shared.util.path_manager import PathManager
from paint_battle_custom_tank.shared.util.randomizer import battle_randomizer


class BrushType(Enum):
    """インク塗布に使用するブラシ形状タイプ。"""

    NOISED_CIRCLE = auto()      # 通常ノイズ円形
    BIG_NOISED_CIRCLE = auto()  # 大サイズノイズ円形
    STRETCHED = auto()          # 引き伸ばし・飛沫形状


@dataclass(frozen=True)
class Brush:
    """2値化されたブラシマスクデータを保持するクラス。"""

    mask: np.ndarray


class BrushProcessor:
    """NumPy配列によるブラシマスクの拡大縮小および回転処理ユーティリティ。"""

    @staticmethod
    def process(mask: np.ndarray, scale: float, direction: Vec3) -> np.ndarray:
        """マスクをスケールおよび回転させて新しいマスク配列を生成する。"""
        scaled = BrushProcessor.scale_mask(mask, scale)
        rotated = BrushProcessor.rotate_mask(scaled, direction)
        return rotated

    @staticmethod
    def scale_mask(mask: np.ndarray, scale: float) -> np.ndarray:
        """最近傍補間によりマスクをスケーリングする。"""
        h, w = mask.shape
        new_h = max(1, int(h * scale))
        new_w = max(1, int(w * scale))

        y_idx = (np.linspace(0, h - 1, new_h)).astype(np.int32)
        x_idx = (np.linspace(0, w - 1, new_w)).astype(np.int32)

        return mask[y_idx[:, None], x_idx[None, :]].astype(np.uint8)

    @staticmethod
    def rotate_mask(mask: np.ndarray, direction: Vec3) -> np.ndarray:
        """指定された方向ベクトルに合わせてマスクを2次元回転する。"""
        dx = direction.x
        dy = direction.y
        angle = np.arctan2(dy, dx)

        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        h, w = mask.shape
        new_w = int(abs(w * cos_a) + abs(h * sin_a))
        new_h = int(abs(w * sin_a) + abs(h * cos_a))

        out = np.zeros((new_h, new_w), dtype=np.uint8)

        cx_new = new_w / 2.0
        cy_new = new_h / 2.0
        cx = w / 2.0
        cy = h / 2.0

        y, x = np.indices((new_h, new_w))
        x0 = x - cx_new
        y0 = y - cy_new

        xr = x0 * cos_a + y0 * sin_a + cx
        yr = -x0 * sin_a + y0 * cos_a + cy

        xi = np.round(xr).astype(int)
        yi = np.round(yr).astype(int)

        valid = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        out[valid] = mask[yi[valid], xi[valid]]

        return out


class BrushFactory:
    """テクスチャ画像からブラシマスクを生成するファクトリ。"""

    @staticmethod
    def create(path: str, shift_distance: int = 0) -> Brush:
        """画像ファイルを読み込み、アルファチャンネルから2値化マスクを生成する。"""
        tex = Texture()
        tex.read(path)
        data = tex.getRamImage()
        arr = np.frombuffer(data, dtype=np.uint8)
        arr = arr.reshape((tex.getYSize(), tex.getXSize(), 4))
        alpha = arr[:, :, 3] / 255.0
        alpha_mask = (alpha >= 0.5).astype(np.uint8)
        mask = BrushFactory._shift_mask_expand_left(alpha_mask, shift_distance)
        return Brush(mask)

    @staticmethod
    def _shift_mask_expand_left(mask: np.ndarray, add_left: int) -> np.ndarray:
        """マスクの左側に余白を追加してシフトする。"""
        if add_left <= 0:
            return mask
        h, w = mask.shape
        new_w = w + add_left
        out = np.zeros((h, new_w), dtype=np.uint8)
        out[:, add_left : add_left + w] = mask
        return out


class BrushManager:
    """各ブラシ種別のマスクテクスチャをロード・管理し、要求に応じたマスクを供給するマネージャ。"""

    def __init__(self) -> None:
        self.__noised_circle_brush_list: list[Brush] = [
            BrushFactory.create(PathManager.resource_vfs("textures/noised_circle_brush_1.png"), 0),
            BrushFactory.create(PathManager.resource_vfs("textures/noised_circle_brush_2.png"), 0),
            BrushFactory.create(PathManager.resource_vfs("textures/noised_circle_brush_3.png"), 0),
        ]

        self.__big_noised_circle_brush_list: list[Brush] = [
            BrushFactory.create(PathManager.resource_vfs("textures/big_noised_circle_brush_1.png"), 0),
            BrushFactory.create(PathManager.resource_vfs("textures/big_noised_circle_brush_2.png"), 0),
            BrushFactory.create(PathManager.resource_vfs("textures/big_noised_circle_brush_3.png"), 0),
        ]

        self.__stretched_brush_list: list[Brush] = [
            BrushFactory.create(PathManager.resource_vfs("textures/stretched_brush_1.png"), 64),
            BrushFactory.create(PathManager.resource_vfs("textures/stretched_brush_2.png"), 64),
            BrushFactory.create(PathManager.resource_vfs("textures/stretched_brush_3.png"), 64),
        ]

        self.__registry: dict[BrushType, list[Brush]] = {
            BrushType.NOISED_CIRCLE: self.__noised_circle_brush_list,
            BrushType.BIG_NOISED_CIRCLE: self.__big_noised_circle_brush_list,
            BrushType.STRETCHED: self.__stretched_brush_list,
        }

    def create_mask(
        self,
        brush_type: BrushType,
        brush_world_radius: float,
        direction: Vec3,
        pixels_per_meter: float
    ) -> np.ndarray:
        """指定されたパラメータに基づき、加工済みの2値マスク配列を生成して返す。"""
        brush_list = self.__registry[brush_type]
        brush = battle_randomizer.choice(brush_list)
        mask = brush.mask
        brush_pixel_radius = brush_world_radius * pixels_per_meter
        mask_pixel_height = mask.shape[0]
        mask_scale = (brush_pixel_radius * 2.0) / mask_pixel_height
        new_mask = BrushProcessor.process(mask, mask_scale, direction)
        return new_mask
