"""カラーパレットおよびマテリアルストレージモジュール。"""

from __future__ import annotations
from dataclasses import dataclass
# pyrefly: ignore [missing-import]
from panda3d.core import Material, Vec4
from paint_battle_custom_tank.graphics.util.yamane_color import ColorConverter


@dataclass(frozen=True)
class ColorData:
    """各色空間およびフォーマット表現を保持するカラーデータクラス。"""

    name: str
    degree_hsv: tuple[int, int, int]
    float_rgb: tuple[float, float, float]
    float_rgb_linear: tuple[float, float, float]
    byte_rgb: tuple[int, int, int]
    byte_rgb_linear: tuple[int, int, int]
    hex: str

    @classmethod
    def from_degree_hsv(cls, name: str, degree_hsv: tuple[int, int, int]) -> ColorData:
        """HSV (度数法) から ColorData を生成する。"""
        srgb_float = ColorConverter.hsv_deg_srgb_to_rgb_srgb(degree_hsv)
        linear_float = ColorConverter.hsv_deg_srgb_to_rgb_linear(degree_hsv)
        return cls(
            name=name,
            degree_hsv=degree_hsv,
            float_rgb=srgb_float,
            float_rgb_linear=linear_float,
            byte_rgb=ColorConverter.rgb_float_to_byte(srgb_float),
            byte_rgb_linear=ColorConverter.rgb_float_to_byte(linear_float),
            hex=ColorConverter.rgb_float_to_hex(srgb_float),
        )


@dataclass(frozen=True)
class ColorStorage:
    """ゲーム内で使用する基本カラーパレットの静的定義。"""

    black: ColorData = ColorData.from_degree_hsv("black", (0, 0, 0))
    white: ColorData = ColorData.from_degree_hsv("white", (0, 0, 100))
    gray: ColorData = ColorData.from_degree_hsv("gray", (0, 0, 50))
    vivid_red: ColorData = ColorData.from_degree_hsv("vivid_red", (2, 71, 100))
    vivid_orange: ColorData = ColorData.from_degree_hsv("vivid_orange", (24, 80, 100))
    vivid_yellow: ColorData = ColorData.from_degree_hsv("vivid_yellow", (60, 80, 100))
    vivid_green: ColorData = ColorData.from_degree_hsv("vivid_green", (123, 80, 82))
    vivid_cyan: ColorData = ColorData.from_degree_hsv("vivid_cyan", (180, 80, 100))
    vivid_blue: ColorData = ColorData.from_degree_hsv("vivid_blue", (236, 80, 90))
    vivid_purple: ColorData = ColorData.from_degree_hsv("vivid_purple", (264, 80, 100))
    vivid_pink: ColorData = ColorData.from_degree_hsv("vivid_pink", (307, 35, 100))

    strong_yellow: ColorData = ColorData.from_degree_hsv("strong_yellow", (59, 91, 86))

    pale_gray: ColorData = ColorData.from_degree_hsv("pale_gray", (0, 0, 90))
    pale_red: ColorData = ColorData.from_degree_hsv("pale_red", (5, 20, 100))
    pale_orange: ColorData = ColorData.from_degree_hsv("pale_orange", (28, 20, 100))
    pale_green: ColorData = ColorData.from_degree_hsv("pale_green", (123, 20, 100))
    pale_cyan: ColorData = ColorData.from_degree_hsv("pale_cyan", (185, 20, 100))
    pale_blue: ColorData = ColorData.from_degree_hsv("pale_blue", (237, 40, 70))
    pale_purple: ColorData = ColorData.from_degree_hsv("pale_purple", (260, 20, 100))

    bright_red: ColorData = ColorData.from_degree_hsv("bright_red", (0, 60, 100))
    bright_blue: ColorData = ColorData.from_degree_hsv("bright_blue", (231, 60, 100))
    dark_purple: ColorData = ColorData.from_degree_hsv("dark_purple", (256, 80, 40))

    ink_blue = ColorData.from_degree_hsv("ink_blue", (237, 73, 76))
    ink_blue_light = ColorData.from_degree_hsv("ink_blue_light", (237, 50, 100))
    ink_blue_dark = ColorData.from_degree_hsv("ink_blue_dark", (237, 60, 50))
    
    ink_orange = ColorData.from_degree_hsv("ink_orange", (21, 78, 98))
    ink_orange_light = ColorData.from_degree_hsv("ink_orange_light", (21, 60, 100))
    ink_orange_dark = ColorData.from_degree_hsv("ink_orange_dark", (21, 70, 50))

    ink_pink = ColorData.from_degree_hsv("ink_pink", (331, 72, 88))
    ink_pink_light = ColorData.from_degree_hsv("ink_pink_light", (331, 50, 100))
    ink_pink_dark = ColorData.from_degree_hsv("ink_pink_dark", (331, 60, 50))

    ink_green = ColorData.from_degree_hsv("ink_green", (115, 75, 78))
    ink_green_light = ColorData.from_degree_hsv("ink_green_light", (115, 50, 100))
    ink_green_dark = ColorData.from_degree_hsv("ink_green_dark", (115, 60, 50))


class MaterialFactory:
    """PBRマテリアルを生成するファクトリクラス。"""

    @staticmethod
    def create_diffuse(degree_hsv: tuple[int, int, int], roughness: float = 1.0) -> Material:
        """非金属（ディフューズ）PBRマテリアルを生成する。"""
        float_rgb_linear = ColorConverter.hsv_deg_srgb_to_rgb_linear(degree_hsv)
        mat = Material("diffuse")
        mat.set_base_color(Vec4(*float_rgb_linear, 1))
        mat.set_metallic(0)
        mat.set_emission(Vec4(0, 0, 0, 1))
        mat.set_roughness(roughness)
        return mat

    @staticmethod
    def create_metallic(degree_hsv: tuple[int, int, int], roughness: float = 0.2) -> Material:
        """金属（メタリック）PBRマテリアルを生成する。"""
        float_rgb_linear = ColorConverter.hsv_deg_srgb_to_rgb_linear(degree_hsv)
        mat = Material("metallic")
        mat.set_base_color(Vec4(*float_rgb_linear, 1))
        mat.set_metallic(1)
        mat.set_emission(Vec4(0, 0, 0, 1))
        mat.set_roughness(roughness)
        return mat

    @staticmethod
    def create_emissive(degree_hsv: tuple[int, int, int], emission_strength: float = 1.0) -> Material:
        """発光PBRマテリアルを生成する。"""
        float_rgb_linear = ColorConverter.hsv_deg_srgb_to_rgb_linear(degree_hsv)
        mat = Material("emissive")
        mat.set_base_color(Vec4(0, 0, 0, 1))
        mat.set_metallic(0)
        mat.set_emission(Vec4(*float_rgb_linear, 1) * emission_strength)
        mat.set_roughness(1.0)
        return mat


@dataclass(frozen=True)
class MaterialStorage:
    """ゲーム内で頻繁に使用されるマテリアルのキャッシュクラス。"""
    black_diff: Material = MaterialFactory.create_diffuse((0, 0, 0), 1.0)
    white_diff: Material = MaterialFactory.create_diffuse((0, 0, 100), 1.0)
    gray_diff: Material = MaterialFactory.create_diffuse((0, 0, 50), 1.0)

    ink_blue_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_blue.degree_hsv, 0.3)
    ink_blue_light_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_blue_light.degree_hsv, 0.3)
    ink_blue_dark_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_blue_dark.degree_hsv, 0.3)

    ink_orange_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_orange.degree_hsv, 0.3)
    ink_orange_light_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_orange_light.degree_hsv, 0.3)
    ink_orange_dark_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_orange_dark.degree_hsv, 0.3)

    ink_pink_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_pink.degree_hsv, 0.3)
    ink_pink_light_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_pink_light.degree_hsv, 0.3)
    ink_pink_dark_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_pink_dark.degree_hsv, 0.3)

    ink_green_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_green.degree_hsv, 0.3)
    ink_green_light_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_green_light.degree_hsv, 0.3)
    ink_green_dark_diff: Material = MaterialFactory.create_diffuse(ColorStorage.ink_green_dark.degree_hsv, 0.3)