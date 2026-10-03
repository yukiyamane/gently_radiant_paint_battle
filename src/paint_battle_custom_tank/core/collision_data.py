"""物理衝突グループおよび接触イベント管理モジュール。"""

from __future__ import annotations
from enum import IntEnum
from direct.showbase.DirectObject import DirectObject
# pyrefly: ignore [missing-import]
from panda3d.bullet import BulletRigidBodyNode, BulletWorld


class CollisionGroup(IntEnum):
    """Bullet物理演算で使用するコリジョングループ識別ビット。"""

    WALL = 0          # 壁・固定障害物
    ALPHA_TANK = 1    # アルファチーム戦車
    ALPHA_BULLET = 2  # アルファチーム弾丸
    BRAVO_TANK = 3    # ブラボーチーム戦車
    BRAVO_BULLET = 4  # ブラボーチーム弾丸
    ALPHA_EMP = 5     # アルファチーム電磁波
    BRAVO_EMP = 6     # ブラボーチーム電磁波


class ContactEventManager(DirectObject):
    """Panda3D Bulletの接触イベントをハンドリングするマネージャクラス。"""

    def __init__(self, world: BulletWorld) -> None:
        """接触イベントマネージャを初期化する。

        Parameters
        ----------
        world : BulletWorld
            対象のBullet物理ワールド。
        """
        super().__init__()
        self.__world = world
        self.accept("bullet-contact-added", self.__on_contact)

    def __on_contact(
        self,
        node0: BulletRigidBodyNode,
        node1: BulletRigidBodyNode
    ) -> None:
        """2つのノードが衝突した際に呼び出されるコールバック。"""
        cb0 = node0.getPythonTag("on_contact")
        cb1 = node1.getPythonTag("on_contact")

        if cb0:
            cb0(node1)
        if cb1:
            cb1(node0)

    def destroy(self) -> None:
        """イベントリスナーを破棄する。"""
        self.ignoreAll()
