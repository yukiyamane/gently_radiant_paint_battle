from enum import Enum, auto
from dataclasses import dataclass


class TankCondition(Enum):
    ALIVE = auto()
    DEAD = auto()
    INVINCIBLE = auto()
    


@dataclass
class TankStatus:
    """戦車のステータス情報。"""

    hp: int = 1000
    max_hp: int = 1000
    sp: float = 0.0
    max_sp: float = 1.0
    condition: TankCondition = TankCondition.ALIVE
    time_since_death: float = 0.0
    pixels_painted: int = 0
    area_painted: float = 0.0
    kill_count: int = 0
    death_count: int = 0
    special_count: int = 0