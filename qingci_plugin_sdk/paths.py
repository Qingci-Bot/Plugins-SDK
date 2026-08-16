"""应用根目录解析 — 插件 SDK 独立版本

与主项目 bot/paths.py 行为一致：
- 源码模式：调用方包根（qingci_plugin_sdk/ 的上级目录）
- frozen 模式（PyInstaller onedir）：exe 所在目录

SDK 的 data_dir/plugins/<name>/ 基于此根解析，保证插件数据
落在宿主应用可写目录，而非 site-packages 内。
"""

import sys
from pathlib import Path

# 可写数据根目录的运行时覆盖（默认 app_root()/data）。
# 宿主应用（Qingci-Bot）加载 SDK 插件时通过 set_data_root() 将其重定向到
# 实例可写数据根（--data-dir / 实例隔离），保证插件数据不落在站内包目录。
_data_root: Path | None = None


def app_root() -> Path:
    """返回应用根目录（绝对路径）"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def set_data_root(path: str | Path) -> None:
    """设置可写数据根目录（宿主应用在加载 SDK 插件时调用）"""
    global _data_root
    _data_root = Path(path).resolve()


def data_root() -> Path:
    """返回可写数据根目录（被覆盖时返回设置值，否则默认 app_root()/data）"""
    if _data_root is not None:
        return _data_root
    return app_root() / "data"
