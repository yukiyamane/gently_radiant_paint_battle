"""ステージ構成要素・ギミック物理演算・インクペイント管理モジュール。"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, override
import numpy as np
# pyrefly: ignore [missing-import]
from panda3d.bullet import (
    BulletBoxShape,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
)
# pyrefly: ignore [missing-import]
from panda3d.core import BitMask32, Point3, TransformState, VBase3, Vec3

from paint_battle_custom_tank.core.battle_event_data import PaintEvent
from paint_battle_custom_tank.core.collision_data import CollisionGroup
from paint_battle_custom_tank.core.paint import BrushManager
from paint_battle_custom_tank.core.setting import TeamType
from paint_battle_custom_tank.graphics.stage import (
    FixedBoxGraphics,
    OrbitPillarGraphics,
    PaintStageGraphics,
    RotationBoxGraphics,
    SlidingBoxGraphics,
    StageGraphics,
)
from paint_battle_custom_tank.shared.util.randomizer import battle_randomizer

if TYPE_CHECKING:
    from paint_battle_custom_tank.core.battle import Battle
    from paint_battle_custom_tank.core.tank import Tank
    from paint_battle_custom_tank.main import MyApp


@dataclass(frozen=True)
class PaintRequest:
    """ペイントキューに蓄積される塗布要求データ。"""

    requester: Tank
    mask: np.ndarray
    pos: Point3
    team_type: TeamType



@dataclass
class PaintStageStatus:
    neutral_ratio: float = 0.0
    alpha_ratio: float = 0.0
    bravo_ratio: float = 0.0
    neutral_area: float = 0.0
    alpha_area: float = 0.0
    bravo_area: float = 0.0
    neutral_pixel_number: int = 0
    alpha_pixel_number: int = 0
    bravo_pixel_number: int = 0


class PaintStage:
    """ステージ全体の2次元インクマップ（NumPy）管理および塗布・面積集計クラス。"""

    def __init__(self, base: MyApp) -> None:
        self.__pixel_width = 1024
        self.__pixel_height = 512
        self.__array = np.zeros(
            (self.__pixel_height, self.__pixel_width), dtype=np.uint8
        )
        self.__chunk_size = 64

        self.__world_min_x = -200.0
        self.__world_max_x = 200.0
        self.__world_min_y = -100.0
        self.__world_max_y = 100.0
        self.__world_width = self.__world_max_x - self.__world_min_x
        self.__world_height = self.__world_max_y - self.__world_min_y
        self.__pixels_per_meter = self.__pixel_width / self.__world_width
        self.__total_pixel_number = self.__pixel_width * self.__pixel_height

        self.__register_dict: dict[TeamType, int] = {
            TeamType.ALPHA: 1,
            TeamType.BRAVO: 2,
        }

        self.__brush_manager = BrushManager()
        self.__paint_queue: list[PaintRequest] = []
        self.__status = PaintStageStatus()
        self.__graphics = PaintStageGraphics(base)

    @property
    def status(self) -> PaintStageStatus:
        return self.__status

    def __calculate_area(self, number_of_pixel: int) -> float:
        ppm = self.__pixels_per_meter
        meter_per_pixel = 1.0 / ppm
        area_per_pixel = meter_per_pixel * meter_per_pixel
        return number_of_pixel * area_per_pixel

    def __update_status(self) -> None:
        """塗り面積ステータスを計算する。"""
        flat = self.__array.ravel()
        counts = np.bincount(flat, minlength=3)
        self.__status.neutral_pixel_number = int(counts[0])
        self.__status.alpha_pixel_number = int(counts[1])
        self.__status.bravo_pixel_number = int(counts[2])
        self.__status.neutral_area = self.__calculate_area(int(counts[0]))
        self.__status.alpha_area = self.__calculate_area(int(counts[1]))
        self.__status.bravo_area = self.__calculate_area(int(counts[2]))
        self.__status.neutral_ratio = int(counts[0]) / self.__total_pixel_number
        self.__status.alpha_ratio = int(counts[1]) / self.__total_pixel_number
        self.__status.bravo_ratio = int(counts[2]) / self.__total_pixel_number


    def update(self) -> None:
        """キュー内の塗布要求をシャッフル処理し、テクスチャへ反映する。"""
        battle_randomizer.shuffle(self.__paint_queue)
        for request in self.__paint_queue:
            num_changed = self.__apply_paint(
                request.mask, request.pos, request.team_type
            )
            area = self.__calculate_area(num_changed)
            request.requester.apply_repaint_area(area)
        self.__paint_queue.clear()

        self.__update_status()
        self.__graphics.apply_paint(self.__array)

    def request_paint(self, event: PaintEvent) -> None:
        """ペイント要求をキューに追加する。"""
        mask = self.__brush_manager.create_mask(
            event.brush_type,
            event.brush_world_radius,
            event.direction,
            self.__pixels_per_meter,
        )
        request = PaintRequest(event.requester, mask, event.pos, event.team_type)
        self.__paint_queue.append(request)

    def __apply_paint(
        self, mask: np.ndarray, pos: Point3, team_type: TeamType
    ) -> int:
        ix, iy = self.__world_to_index(pos)
        h, w = mask.shape
        array_h, array_w = self.__array.shape

        x1 = ix - w // 2
        y1 = iy - h // 2
        x2 = x1 + w
        y2 = y1 + h

        x1_clip = max(0, x1)
        y1_clip = max(0, y1)
        x2_clip = min(array_w, x2)
        y2_clip = min(array_h, y2)

        chunk = self.__chunk_size
        chunk_x1 = x1_clip // chunk
        chunk_y1 = y1_clip // chunk
        chunk_x2 = (x2_clip - 1) // chunk
        chunk_y2 = (y2_clip - 1) // chunk

        color_id = self.__register_dict[team_type]
        total_changed = 0

        for cy in range(chunk_y1, chunk_y2 + 1):
            for cx in range(chunk_x1, chunk_x2 + 1):
                cx1 = cx * chunk
                cy1 = cy * chunk
                cx2 = min(cx1 + chunk, array_w)
                cy2 = min(cy1 + chunk, array_h)

                ox1 = max(cx1, x1_clip)
                oy1 = max(cy1, y1_clip)
                ox2 = min(cx2, x2_clip)
                oy2 = min(cy2, y2_clip)

                if ox1 >= ox2 or oy1 >= oy2:
                    continue

                region = self.__array[oy1:oy2, ox1:ox2]
                mx1 = ox1 - x1
                my1 = oy1 - y1
                mx2 = ox2 - x1
                my2 = oy2 - y1

                mask_region = mask[my1:my2, mx1:mx2]
                paint_target = mask_region == 1
                changed = int(np.sum(region[paint_target] != color_id))
                total_changed += changed
                region[paint_target] = color_id

        return total_changed

    def __world_to_index(self, pos: Vec3) -> tuple[int, int]:
        ix = int(
            (pos.x - self.__world_min_x) / self.__world_width * self.__pixel_width
        )
        iy = int(
            (pos.y - self.__world_min_y) / self.__world_height * self.__pixel_height
        )
        return (ix, iy)



class StageMode(Enum):
    GIMMICK_ACTIVE = auto()
    GIMMICK_INACTIVE = auto()


class Stage(ABC):
    """ステージの抽象基底クラス。"""
    def __init__(self, base: MyApp) -> None:
        self.__paint_stage: PaintStage = PaintStage(base)

    @property
    def paint_stage(self) -> PaintStage:
        return self.__paint_stage

    @abstractmethod
    def pre_physics_update(self, game_time: float) -> None:
        """物理演算実行前のギミック移動更新。"""
        pass

    @abstractmethod
    def post_physics_update(self, game_time: float) -> None:
        """物理演算実行後のペイント・後処理更新。"""
        pass


class ElectricCountry(Stage):
    """エレクトリックカントリーステージ（固定壁・回転壁・周回柱・スライド壁配置）。"""

    def __init__(self, base: MyApp, battle: Battle) -> None:
        super().__init__(base)
        self.__base = base
        world = battle.physics_world

        self.__wall_top = FixedBox(
            base, world, VBase3(160, 20, 10), Point3(0, 120, 0)
        )
        self.__wall_bottom = FixedBox(
            base, world, VBase3(160, 20, 10), Point3(0, -120, 0)
        )
        self.__wall_right = FixedBox(
            base, world, VBase3(20, 20, 10), Point3(220, 0, 0)
        )
        self.__wall_left = FixedBox(
            base, world, VBase3(20, 20, 10), Point3(-220, 0, 0)
        )

        radius = Vec3(10, 3, 5)
        pos_list = [
            Point3(100, 50, 0),
            Point3(100, -50, 0),
            Point3(-100, 50, 0),
            Point3(-100, -50, 0),
        ]
        rotation_speed_list = [20.0, -20.0, -20.0, 20.0]

        self.__rotation_box_list: list[RotatingBox] = []
        for i in range(4):
            pos = pos_list[i]
            speed = rotation_speed_list[i] * 4.0
            box = RotatingBox(base, world, radius, pos, speed)
            self.__rotation_box_list.append(box)
        rb_center = RotatingBox(base, world, VBase3(20, 3, 5), Point3(0, 0, 0), 120.0)
        self.__rotation_box_list.append(rb_center)

        self.__orbit_pillar_list: list[OrbitPillar] = [
            OrbitPillar(base, world, 15.0, Point3(0, 0, 0), 50.0, 30.0, 0.0),
            OrbitPillar(base, world, 15.0, Point3(0, 0, 0), 50.0, 30.0, 180.0),
        ]

        self.__sliding_box_list: list[SlidingBox] = []

        sb_l1 = SlidingBox(
            base, world, Vec3(20, 40, 10), Vec3(-220, 60, 0), Vec3(1, 0, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_l1.start_with_push()
        self.__sliding_box_list.append(sb_l1)

        sb_l2 = SlidingBox(
            base, world, Vec3(20, 40, 10), Vec3(-220, -60, 0), Vec3(1, 0, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_l2.start_with_push()
        self.__sliding_box_list.append(sb_l2)

        sb_l3 = SlidingBox(
            base, world, Vec3(20, 20, 10), Vec3(-180, -120, 0), Vec3(0, 1, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_l3.start_with_pull_hold()
        self.__sliding_box_list.append(sb_l3)

        sb_l4 = SlidingBox(
            base, world, Vec3(20, 20, 10), Vec3(-180, 120, 0), Vec3(0, -1, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_l4.start_with_pull_hold()
        self.__sliding_box_list.append(sb_l4)

        sb_top = SlidingBox(
            base, world, Vec3(5, 20, 10), Vec3(100, 110, 0), Vec3(-1, 0, 0), 200.0, 4.0, 1.0, 4.0, 1.0
        )
        sb_top.start_with_push()
        self.__sliding_box_list.append(sb_top)

        sb_bottom = SlidingBox(
            base, world, Vec3(5, 20, 10), Vec3(-100, -110, 0), Vec3(1, 0, 0), 200.0, 4.0, 1.0, 4.0, 1.0
        )
        sb_bottom.start_with_push()
        self.__sliding_box_list.append(sb_bottom)

        sb_r1 = SlidingBox(
            base, world, Vec3(20, 40, 10), Vec3(220, 60, 0), Vec3(-1, 0, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_r1.start_with_push()
        self.__sliding_box_list.append(sb_r1)

        sb_r2 = SlidingBox(
            base, world, Vec3(20, 40, 10), Vec3(220, -60, 0), Vec3(-1, 0, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_r2.start_with_push()
        self.__sliding_box_list.append(sb_r2)

        sb_r3 = SlidingBox(
            base, world, Vec3(20, 20, 10), Vec3(180, -120, 0), Vec3(0, 1, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_r3.start_with_pull_hold()
        self.__sliding_box_list.append(sb_r3)

        sb_r4 = SlidingBox(
            base, world, Vec3(20, 20, 10), Vec3(180, 120, 0), Vec3(0, -1, 0), 40.0, 2.0, 1.0, 2.0, 5.0
        )
        sb_r4.start_with_pull_hold()
        self.__sliding_box_list.append(sb_r4)

        self.__stage_graphics = StageGraphics(base)


    @override
    def pre_physics_update(self, game_time: float) -> None:
        for orbit_pillar in self.__orbit_pillar_list:
            orbit_pillar.update(game_time)
        for rotation_box in self.__rotation_box_list:
            rotation_box.update(game_time)
        for sliding_box in self.__sliding_box_list:
            sliding_box.update(game_time)

    @override
    def post_physics_update(self, game_time: float) -> None:
        self.paint_stage.update()


class OrbitPillar:
    """中心点の周囲を一定速度で周回するキネマティック柱。"""

    def __init__(
        self,
        base: MyApp,
        physics_world: BulletWorld,
        radius: float,
        pivot: Point3,
        distance_from_pivot: float,
        revolution_speed: float,
        initial_degree: float,
    ) -> None:
        shape = BulletSphereShape(radius)
        node = BulletRigidBodyNode("orbit_pillar")
        node.addShape(shape)
        node.setRestitution(1.0)
        node.setMass(0)
        node.setKinematic(True)
        physics_world.attachRigidBody(node)

        self.__node = node
        self.__graphics = OrbitPillarGraphics(base, radius)
        self.__pivot = pivot
        self.__distance_from_pivot = distance_from_pivot
        self.__revolution_speed = revolution_speed
        self.__initial_degree = initial_degree
        self.update(0.0)

    def update(self, game_time: float) -> None:
        current_degree = (
            self.__initial_degree + (self.__revolution_speed * game_time)
        ) % 360.0
        rad = np.deg2rad(current_degree)
        offset_x = self.__distance_from_pivot * np.cos(rad)
        offset_y = self.__distance_from_pivot * np.sin(rad)
        new_pos = self.__pivot + Point3(offset_x, offset_y, 0)
        self.__node.setTransform(TransformState.makePos(new_pos))
        self.__graphics.set_pos(new_pos)


class FixedBox:
    """位置・回転が固定された静的障害物壁。"""

    def __init__(
        self, base: MyApp, world: BulletWorld, radius: VBase3, pos: Point3
    ) -> None:
        box_shape = BulletBoxShape(radius)
        box_node = BulletRigidBodyNode("box")
        box_node.addShape(box_shape)
        box_node.setRestitution(1.0)
        box_node.setMass(0)
        box_node.setStatic(True)
        box_node.setTransform(TransformState.makePos(pos))
        box_node.setIntoCollideMask(BitMask32.bit(CollisionGroup.WALL))
        world.attachRigidBody(box_node)

        self.__graphics = FixedBoxGraphics(base, radius)
        self.__graphics.set_pos(pos)


class RotatingBox:
    """その場でZ軸回転し続けるキネマティック障害物。"""

    def __init__(
        self,
        base: MyApp,
        world: BulletWorld,
        radius: Vec3,
        pos: Point3,
        rotation_speed: float,
    ) -> None:
        shape = BulletBoxShape(radius)
        box_node = BulletRigidBodyNode("box")
        box_node.addShape(shape)
        box_node.setRestitution(1.0)
        box_node.setMass(0)
        box_node.setKinematic(True)
        box_node.setTransform(TransformState.makePos(pos))
        box_node.setIntoCollideMask(BitMask32.bit(CollisionGroup.WALL))
        world.attachRigidBody(box_node)

        self.__rotation_speed = rotation_speed
        self.__node = box_node
        self.__fixed_pos = pos
        self.__graphics = RotationBoxGraphics(base, radius)
        self.__graphics.set_pos(pos)
        self.update(0.0)

    def update(self, game_time: float) -> None:
        current_h = (self.__rotation_speed * game_time) % 360.0
        new_hpr = Vec3(current_h, 0.0, 0.0)
        new_ts = TransformState.makePosHpr(self.__fixed_pos, new_hpr)
        self.__node.setTransform(new_ts)
        self.__graphics.set_hpr(new_hpr)


class SlidingBox:
    """イージングで往復スライドするキネマティック障害物壁。"""

    def __init__(
        self,
        base: MyApp,
        world: BulletWorld,
        radius: Vec3,
        pos: Vec3,
        push_axis: Vec3,
        max_offset: float,
        push_duration: float,
        push_hold_duration: float,
        pull_duration: float,
        pull_hold_duration: float,
    ) -> None:
        shape = BulletBoxShape(radius)
        box_node = BulletRigidBodyNode("box")
        box_node.addShape(shape)
        box_node.setRestitution(1.0)
        box_node.setMass(0)
        box_node.setKinematic(True)
        box_node.setTransform(TransformState.makePos(pos))
        box_node.setIntoCollideMask(BitMask32.bit(CollisionGroup.WALL))
        world.attachRigidBody(box_node)

        self.__node = box_node
        self.__push_axis = push_axis
        self.__base_pos = pos
        self.__max_offset = max_offset
        self.__push_duration = push_duration
        self.__push_hold_duration = push_hold_duration
        self.__pull_duration = pull_duration
        self.__pull_hold_duration = pull_hold_duration
        self.__loop_duration = (
            push_duration + push_hold_duration + pull_duration + pull_hold_duration
        )
        self.__time_offset = 0.0

        self.__graphics = SlidingBoxGraphics(base, radius)
        self.__graphics.set_pos(pos)

    def start_with_push(self) -> None:
        self.__time_offset = 0.0

    def start_with_pull_hold(self) -> None:
        self.__time_offset = (
            self.__push_duration + self.__push_hold_duration + self.__pull_duration
        )

    def __ease_in_out(self, t: float) -> float:
        if t < 0.5:
            return 2.0 * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0

    def update(self, game_time: float) -> None:
        total_time = game_time + self.__time_offset
        local_time = total_time % self.__loop_duration

        t1 = self.__push_duration
        t2 = t1 + self.__push_hold_duration
        t3 = t2 + self.__pull_duration

        if local_time < t1:
            t = local_time / self.__push_duration
            offset = self.__ease_in_out(t) * self.__max_offset
        elif local_time < t2:
            offset = self.__max_offset
        elif local_time < t3:
            time_in_pull = local_time - t2
            t = time_in_pull / self.__pull_duration
            offset = (1.0 - self.__ease_in_out(t)) * self.__max_offset
        else:
            offset = 0.0

        self.__apply_offset(offset)

    def __apply_offset(self, offset: float) -> None:
        new_pos = self.__base_pos + self.__push_axis * offset
        self.__node.setTransform(TransformState.makePos(new_pos))
        self.__graphics.set_pos(new_pos)
