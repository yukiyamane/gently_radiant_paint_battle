"""リソース（3Dモデル・プリミティブ・フォント・マテリアル）一括管理モジュール。"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field
from direct.showbase.ShowBase import ShowBase
# pyrefly: ignore [missing-import]
from panda3d.core import DynamicTextFont, NodePath, FontPool
from paint_battle_custom_tank.graphics.material import ColorStorage, MaterialStorage
from paint_battle_custom_tank.shared.util.path_manager import PathManager


@dataclass(frozen=True)
class ResourceContext:
    """アプリケーション全体で共有される各種グラフィックスリソースのコンテキスト。"""

    base: ShowBase
    primitive_model: PrimitiveModel = field(init=False)
    model: Model = field(init=False)
    font: YamaneFont = field(init=False)
    color_storage: ColorStorage = field(init=False)
    material_storage: MaterialStorage = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "primitive_model", PrimitiveModel(self.base))
        object.__setattr__(self, "model", Model(self.base))
        object.__setattr__(self, "font", YamaneFont(self.base))
        object.__setattr__(self, "color_storage", ColorStorage())
        object.__setattr__(self, "material_storage", MaterialStorage())


class PrimitiveModel:
    """基本幾何学形状（プリミティブモデル）のロード・キャッシュクラス。"""

    def __init__(self, base: ShowBase) -> None:
        self.__tetrahedron: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/tetrahedron.egg")
        )
        self.__octahedron: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/octahedron.egg")
        )
        self.__dodecahedron: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/dodecahedron.egg")
        )
        self.__icosahedron: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/icosahedron.egg")
        )
        self.__cube_2m: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/cube_2m.egg")
        )
        self.__cube_2m_for_emi: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/cube_2m_for_emi.egg")
        )
        self.__cube_2m_origin: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/cube_2m_origin_offset.egg")
        )
        self.__plane_2m: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/plane_2m.egg")
        )
        self.__sphere_2m: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/sphere_2m.egg")
        )
        self.__ico_sphere_2m: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/ico_sphere_2m.glb")
        )
        self.__cylinder_2m: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("solids/cylinder_2m.bam")
        )

    @property
    def tetrahedron(self) -> NodePath:
        return self.__tetrahedron

    @property
    def octahedron(self) -> NodePath:
        return self.__octahedron

    @property
    def dodecahedron(self) -> NodePath:
        return self.__dodecahedron

    @property
    def icosahedron(self) -> NodePath:
        return self.__icosahedron

    @property
    def cube_2m(self) -> NodePath:
        return self.__cube_2m

    @property
    def cube_2m_for_emi(self) -> NodePath:
        return self.__cube_2m_for_emi

    @property
    def cube_2m_origin(self) -> NodePath:
        return self.__cube_2m_origin

    @property
    def plane_2m(self) -> NodePath:
        return self.__plane_2m

    @property
    def sphere_2m(self) -> NodePath:
        return self.__sphere_2m

    @property
    def ico_sphere_2m(self) -> NodePath:
        return self.__ico_sphere_2m

    @property
    def cylinder_2m(self) -> NodePath:
        return self.__cylinder_2m


class Model:
    """専用3Dモデル（glb / egg）のロード・キャッシュクラス。"""

    def __init__(self, base: ShowBase) -> None:
        self.__missile_bullet: NodePath = base.loader.loadModel(
            PathManager.resource_vfs("models/special_missile_bullet.glb")
        )

    @property
    def missile_bullet(self) -> NodePath:
        return self.__missile_bullet


class YamaneFont:
    """フォントリソースのロード・キャッシュクラス。"""

    def __init__(self, base: ShowBase) -> None:
        self.__noto_mono: DynamicTextFont = base.loader.loadFont(
            PathManager.resource_vfs("fonts/noto/NotoSansMonoCJKjp-Bold.otf")
        )
        self.__noto_mono.setPixelsPerUnit(120)
        self.__noto_mono.setPageSize(1024, 1024)

        self.__mplus_bold: DynamicTextFont = base.loader.loadFont(
            PathManager.resource_vfs("fonts/mplus/MPLUSRounded1c-Bold.ttf")
        )
        self.__mplus_bold.setPixelsPerUnit(120)
        self.__mplus_bold.setPageSize(1024, 1024)

        self.__mplus_bold_hq: DynamicTextFont = base.loader.loadFont(
            PathManager.resource_vfs("fonts/mplus/MPLUSRounded1c-Bold-HQ.ttf")
        )
        self.__mplus_bold_hq.setPixelsPerUnit(240)
        self.__mplus_bold_hq.setPageSize(2048, 2048)

        self.__mplus_regular: DynamicTextFont = base.loader.loadFont(
            PathManager.resource_vfs("fonts/mplus/MPLUSRounded1c-Regular.ttf")
        )
        self.__mplus_regular.setPixelsPerUnit(120)
        self.__mplus_regular.setPageSize(1024, 1024)

        self.__yujisyuku_regular: DynamicTextFont = base.loader.loadFont(
            PathManager.resource_vfs("fonts/yujisyuku/YujiSyuku-Regular.ttf")
        )
        self.__yujisyuku_regular.setPixelsPerUnit(240)
        self.__yujisyuku_regular.setPageSize(2048, 2048)

    @property
    def noto_mono(self) -> DynamicTextFont:
        return self.__noto_mono

    @property
    def mplus_bold(self) -> DynamicTextFont:
        return self.__mplus_bold

    @property
    def mplus_bold_hq(self) -> DynamicTextFont:
        return self.__mplus_bold_hq

    @property
    def mplus_regular(self) -> DynamicTextFont:
        return self.__mplus_regular

    @property
    def yujisyuku_regular(self) -> DynamicTextFont:
        return self.__yujisyuku_regular


class FontManager:
    def __init__(self):
        self.cache = {}  # {(font_path, fg, outline_color, width): font}

    def get_font(
        self,
        font_path: str,
        fg: tuple[float, float, float, float] = (1, 1, 1, 1),
        outline_color: Optional[tuple[float, float, float, float]] = None,
        outline_width: float = 0.0,
    ) -> DynamicTextFont:
        key = (font_path, fg, outline_color, outline_width)

        # 既にキャッシュ済みならそれを返す
        if key in self.cache:
            return self.cache[key]

        # 新規ロード
        font = FontPool.loadFont(font_path)

        # 文字色
        font.setFg(fg)

        # 縁取り
        if outline_color is not None:
            font.setOutline(outline_color, outline_width, 0)

        self.cache[key] = font
        return font

"""
#テスト
fm = FontManager()
# 白文字＋黒縁取り
font_white_black = fm.get_font(
    PathManager.resource_vfs("fonts/mplus/MPLUSRounded1c-Bold.ttf"),
    fg=(1,1,1,1),
    outline_color=(0,0,0,1),
    outline_width=0.5
)
# 赤文字＋黒縁取り
font_red_black = fm.get_font(
    PathManager.resource_vfs("fonts/mplus/MPLUSRounded1c-Bold.ttf"),
    fg=(1,0,0,1),
    outline_color=(0,0,0,1),
    outline_width=0.5
)
# 黄色文字（縁取りなし）
font_yellow = fm.get_font(
    PathManager.resource_vfs("fonts/mplus/MPLUSRounded1c-Bold.ttf"),
    fg=(1,1,0,1),
    outline_color=None
)
"""