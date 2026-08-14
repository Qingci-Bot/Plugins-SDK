"""应用根目录解析 — 插件 SDK 独立版本

与主项目 bot/paths.py 行为一致：
- 源码模式：调用方包根（qingci_plugin_sdk/ 的上级目录）
- frozen 模式（PyInstaller onedir）：exe 所在目录

SDK 的 data_dir/plugins/<name>/ 基于此根解析，保证插件数据
落在宿主应用可写目录，而非 site-packages 内。
"""

import sys
from pathlib import Path


def app_root() -> Path:
    """返回应用根目录（绝对路径）"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent