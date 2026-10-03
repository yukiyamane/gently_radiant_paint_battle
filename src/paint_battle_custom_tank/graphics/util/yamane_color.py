"""色空間変換およびガンマ補正ユーティリティモジュール。"""

from __future__ import annotations
import colorsys


class ColorConverter:
    """色空間（sRGB / Linear RGB / HSV）およびデータ型（Float / Byte / Hex）の相互変換クラス。"""

    # ------------------------------------------------------------
    # ガンマ変換 (sRGB <-> Linear)
    # ------------------------------------------------------------
    @staticmethod
    def srgb_to_linear(c: float) -> float:
        """sRGBの単一チャンネル値 (0.0〜1.0) をリニア値に変換する。"""
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    @staticmethod
    def linear_to_srgb(c: float) -> float:
        """リニアの単一チャンネル値 (0.0〜1.0) をsRGB値に変換する。"""
        if c <= 0.0031308:
            return 12.92 * c
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    @staticmethod
    def rgb_float_to_linear(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
        """sRGB floatタプルをリニア floatタプルに変換する。"""
        r, g, b = rgb
        return (
            ColorConverter.srgb_to_linear(r),
            ColorConverter.srgb_to_linear(g),
            ColorConverter.srgb_to_linear(b),
        )

    @staticmethod
    def rgb_float_to_srgb(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
        """リニア floatタプルをsRGB floatタプルに変換する。"""
        r, g, b = rgb
        return (
            ColorConverter.linear_to_srgb(r),
            ColorConverter.linear_to_srgb(g),
            ColorConverter.linear_to_srgb(b),
        )

    @staticmethod
    def rgb_float_to_byte(rgb: tuple[float, float, float]) -> tuple[int, int, int]:
        """float RGB (0.0〜1.0) を 8bit byte RGB (0〜255) に変換する。"""
        r, g, b = rgb
        return (round(r * 255), round(g * 255), round(b * 255))

    @staticmethod
    def rgb_float_to_hex(rgb: tuple[float, float, float]) -> str:
        """float RGB を 16進数カラーコード文字列（例: #ffffff）に変換する。"""
        r, g, b = rgb
        return "#%02x%02x%02x" % (
            int(r * 255),
            int(g * 255),
            int(b * 255),
        )

    # ------------------------------------------------------------
    # HSV (0〜360 deg, 0〜100%) -> RGB
    # ------------------------------------------------------------
    @staticmethod
    def hsv_deg_linear_to_rgb_linear(hsv: tuple[int, int, int]) -> tuple[float, float, float]:
        """HSV (度数法) からリニアRGB floatを生成する。"""
        h = hsv[0] / 360.0
        s = hsv[1] / 100.0
        v = hsv[2] / 100.0
        return colorsys.hsv_to_rgb(h, s, v)

    @staticmethod
    def hsv_deg_linear_to_rgb_srgb(hsv: tuple[int, int, int]) -> tuple[float, float, float]:
        """HSV (度数法) からsRGB floatを生成する。"""
        rgb_lin = ColorConverter.hsv_deg_linear_to_rgb_linear(hsv)
        return ColorConverter.rgb_float_to_srgb(rgb_lin)

    @staticmethod
    def hsv_deg_srgb_to_rgb_linear(hsv: tuple[int, int, int]) -> tuple[float, float, float]:
        """sRGBガンマ補正済みのHSV (度数法) からリニアRGB floatを生成する。"""
        h = hsv[0] / 360.0
        s_srgb = hsv[1] / 100.0
        v_srgb = hsv[2] / 100.0
        rgb_s = colorsys.hsv_to_rgb(h, s_srgb, v_srgb)
        return ColorConverter.rgb_float_to_linear(rgb_s)

    @staticmethod
    def hsv_deg_srgb_to_rgb_srgb(hsv: tuple[int, int, int]) -> tuple[float, float, float]:
        """sRGBガンマ補正済みのHSV (度数法) からsRGB floatを生成する。"""
        h = hsv[0] / 360.0
        s_srgb = hsv[1] / 100.0
        v_srgb = hsv[2] / 100.0
        return colorsys.hsv_to_rgb(h, s_srgb, v_srgb)

    # ------------------------------------------------------------
    # 輝度計算
    # ------------------------------------------------------------
    @staticmethod
    def luminance_linear(rgb: tuple[float, float, float]) -> float:
        """リニアRGBから相対輝度を計算する。"""
        r, g, b = rgb
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @staticmethod
    def luminance_srgb(rgb: tuple[float, float, float]) -> float:
        """sRGBから相対輝度を計算する。"""
        r_lin, g_lin, b_lin = ColorConverter.rgb_float_to_linear(rgb)
        return ColorConverter.luminance_linear((r_lin, g_lin, b_lin))
