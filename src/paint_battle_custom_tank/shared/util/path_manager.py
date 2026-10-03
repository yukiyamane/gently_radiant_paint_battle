"""リソースパスおよびVFSパス管理モジュール。"""

from __future__ import annotations
from pathlib import Path
import re


class PathManager:
    """プロジェクト内のリソースパスおよびPanda3D VFSパスの解決を行うユーティリティクラス。"""

    PROJECT_ROOT: Path = Path(__file__).resolve().parents[4]
    RESOURCE_DIR: Path = PROJECT_ROOT / "resources"

    @staticmethod
    def to_vfs(path: Path) -> str:
        """Windowsの絶対パスをPanda3DのVFS（Virtual File System）形式に変換する。

        Parameters
        ----------
        path : Path
            対象のファイルパス。

        Returns
        -------
        str
            Panda3D VFS形式のパス文字列（例: /d/path/to/file）。
        """
        posix = path.as_posix()
        # Windows ドライブレターを検出 (例: D:/ -> /d/)
        match = re.match(r"([A-Za-z]):/(.*)", posix)
        if match:
            drive = match.group(1).lower()
            rest = match.group(2)
            return f"/{drive}/{rest}"
        return posix

    @classmethod
    def resource(cls, *paths: str) -> Path:
        """resourcesディレクトリ配下のPathオブジェクトを取得する。

        Parameters
        ----------
        *paths : str
            リソースディレクトリからの相対パス構成要素。

        Returns
        -------
        Path
            解決されたリソースのPathオブジェクト。
        """
        return cls.RESOURCE_DIR.joinpath(*paths)

    @classmethod
    def resource_vfs(cls, *paths: str) -> str:
        """resourcesディレクトリ配下のパスをPanda3D VFS形式文字列として取得する。

        Parameters
        ----------
        *paths : str
            リソースディレクトリからの相対パス構成要素。

        Returns
        -------
        str
            Panda3D VFS形式のパス文字列。
        """
        p = cls.RESOURCE_DIR.joinpath(*paths)
        return cls.to_vfs(p)