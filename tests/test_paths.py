"""paths 测试 — 应用根定位与可写数据根覆盖"""

from __future__ import annotations

import sys

from qingci_plugin_sdk import paths


def test_app_root_points_to_repo_root():
    """源码模式下应用根为 qingci_plugin_sdk/ 的上级目录"""
    root = paths.app_root()
    assert (root / "qingci_plugin_sdk").is_dir()


def test_app_root_frozen_uses_executable_dir(monkeypatch, tmp_path):
    """frozen 模式（PyInstaller）以 exe 所在目录为根"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bot.exe"))
    assert paths.app_root() == tmp_path


def test_data_root_defaults_to_app_root_data(monkeypatch):
    monkeypatch.setattr(paths, "_data_root", None)
    assert paths.data_root() == paths.app_root() / "data"


def test_set_data_root_overrides_default(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "_data_root", None)
    paths.set_data_root(tmp_path)
    assert paths.data_root() == tmp_path.resolve()
