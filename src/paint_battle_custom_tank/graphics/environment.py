"""シーンライティングおよび環境設定モジュール。"""

from __future__ import annotations
from direct.showbase.ShowBase import ShowBase
# pyrefly: ignore [missing-import]
from panda3d.core import AmbientLight, DirectionalLight, NodePath


class Environment:
    """平行光源・環境光・影設定を管理するクラス。"""

    def __init__(self, base: ShowBase) -> None:
        self.__base = base
        self.__sun_lamp: NodePath = self.__create_sun_light()
        self.__ambient_lamp: NodePath = self.__create_ambient_light()

    def __create_sun_light(self) -> NodePath:
        sun_light = DirectionalLight("dlight")
        sun_light.setColor((3.0, 3.0, 3.0, 1.0))
        sun_light.setShadowCaster(True, 1024, 1024)

        sun_lamp = self.__base.render.attachNewNode(sun_light)
        self.__base.render.setLight(sun_lamp)
        sun_lamp.setPos(-100, -100, 200)
        sun_lamp.lookAt(0, 0, 0)
        sun_lamp.node().getLens().setFilmSize(500, 500)
        sun_lamp.node().getLens().setNearFar(1, 500)
        return sun_lamp

    def __create_ambient_light(self) -> NodePath:
        ambient_light = AmbientLight("my_ambient")
        ambient_light.setColor((0.5, 0.5, 0.5, 1.0))
        ambient_lamp = self.__base.render.attachNewNode(ambient_light)
        self.__base.render.setLight(ambient_lamp)
        return ambient_lamp
