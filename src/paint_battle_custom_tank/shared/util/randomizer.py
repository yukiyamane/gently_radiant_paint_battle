"""乱数ジェネレーター管理モジュール。"""

from __future__ import annotations
import random
from typing import Any, Sequence, TypeVar

T = TypeVar("T")


class LoggedRNG:
    """乱数生成履歴を記録可能な乱数ラッパークラス。"""

    def __init__(self, seed: int, name: str) -> None:
        self.rng = random.Random(seed)
        self.name = name
        self.log: list[tuple[str, str, Any, Any]] = []

    def randint(self, a: int, b: int) -> int:
        """指定範囲 [a, b] の整数乱数を生成する。"""
        value = self.rng.randint(a, b)
        self.log.append((self.name, "randint", (a, b), value))
        return value

    def random(self) -> float:
        """[0.0, 1.0) の浮動小数点乱数を生成する。"""
        value = self.rng.random()
        self.log.append((self.name, "random", None, value))
        return value

    def choice(self, seq: Sequence[T]) -> T:
        """シーケンスからランダムに1要素を選択する。"""
        value = self.rng.choice(seq)
        self.log.append((self.name, "choice", seq, value))
        return value


seed_base: int = 999
battle_randomizer: random.Random = random.Random(seed_base + 1)
fx_randomizer: random.Random = random.Random(seed_base + 2)