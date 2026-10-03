"""汎用ステートマシンモジュール。"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class StateContext:
    """ステート実行時に渡されるコンテキスト情報。

    Attributes
    ----------
    current_raw_time : float
        アプリケーションの絶対時間（globalClock.getFrameTime()）。
    dt : float
        このフレームで進めるべきデルタ時間（秒）。
    state_time : float
        現在のステートが開始してからの経過時間（秒）。
    is_first : bool
        ステート遷移直後の最初の実行フレームかどうか。
    """

    current_raw_time: float
    dt: float
    state_time: float
    state_frame: int
    is_first: bool


class StateMachine:
    """累積誤差を排除した時間追従型ステートマシン。"""

    def __init__(self, owner: Any) -> None:
        """ステートマシンを初期化する。

        Parameters
        ----------
        owner : Any
            このステートマシンを保持するオーナーオブジェクト。
        """
        self.__owner = owner
        self.__current_state: Optional[Callable[[StateContext], None]] = None
        self.__next_state: Optional[Callable[[StateContext], None]] = None

        self.__state_start_time: float = 0.0  # ステート開始時のアプリ絶対時間
        self.__overflow_time: float = 0.0     # 遷移時に持ち越されたあふれ時間
        self.__state_frame: int = 0

    @property
    def current_state(self) -> Optional[Callable[[StateContext], None]]:
        """現在アクティブなステート関数を取得する。"""
        return self.__current_state

    def update(self, current_raw_time: float, frame_dt: float) -> None:
        """ステートマシンの更新を実行する。

        Parameters
        ----------
        current_raw_time : float
            アプリケーションの絶対時間。
        frame_dt : float
            1フレームのデルタ時間。
        """
        # 1. 通常実行（遷移要求がない場合）
        if self.__current_state and not self.__next_state:
            state_time = current_raw_time - self.__state_start_time
            self.__state_frame += 1
            ctx = StateContext(
                current_raw_time=current_raw_time,
                dt=frame_dt,
                state_time=state_time,
                state_frame=self.__state_frame,
                is_first=False
            )
            self.__current_state(ctx)

        # 2. 即時遷移の実行
        while self.__next_state:
            current_overflow = self.__overflow_time
            self.__overflow_time = 0.0

            self.__current_state = self.__next_state
            self.__next_state = None

            # あふれた分（過去）に遡って、新しいステートの開始時間を設定
            self.__state_start_time = current_raw_time - current_overflow

            self.__state_frame = 0
            ctx = StateContext(
                current_raw_time=current_raw_time,
                dt=current_overflow if current_overflow > 0.0 else frame_dt,
                state_time=current_overflow,
                state_frame=self.__state_frame,
                is_first=True
            )
            self.__current_state(ctx)

    def set_next_state(
        self,
        state: Callable[[StateContext], None],
        overflow_time: float = 0.0
    ) -> None:
        """次に遷移するステートを設定する。

        Parameters
        ----------
        state : Callable[[StateContext], None]
            遷移先ステート関数。
        overflow_time : float, optional
            前のステートから持ち越された余剰時間（秒）、デフォルトは 0.0。
        """
        self.__next_state = state
        self.__overflow_time = overflow_time
