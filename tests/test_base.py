"""PluginBase 测试

覆盖三块此前没有直接测试的行为：
1. get_exports 的两个失败分支（未注入 bot / 依赖插件未加载）
2. 弃用钩子被覆写时的加载期告警（否则插件作者拿不到任何信号）
3. register_page 的 static_dir 自动探测
"""

from __future__ import annotations

import logging

import pytest

from qingci_plugin_sdk import PluginBase


class _DummyPlugin(PluginBase):
    """最小可用插件（满足两个抽象方法）"""

    name = "dummy"

    async def on_load(self):
        return None

    async def on_unload(self):
        return None


class _FakeBot:
    """替身宿主：只提供 get_exports 需要的 plugin_manager"""

    def __init__(self, plugins: dict | None = None):
        self.plugin_manager = _FakeManager(plugins or {})


class _FakeManager:
    def __init__(self, plugins: dict):
        self._plugins = plugins

    def get(self, name):
        return self._plugins.get(name)


class _Exported:
    _exports = {"answer": 42}


# ---- get_exports ----


def test_get_exports_raises_when_bot_missing():
    plugin = _DummyPlugin()
    with pytest.raises(RuntimeError, match="未初始化"):
        plugin.get_exports("other")


def test_get_exports_raises_when_dependency_not_loaded():
    plugin = _DummyPlugin()
    plugin.bot = _FakeBot({})
    with pytest.raises(RuntimeError, match="依赖插件"):
        plugin.get_exports("missing")


def test_get_exports_returns_dependency_exports():
    plugin = _DummyPlugin()
    plugin.bot = _FakeBot({"other": _Exported()})
    assert plugin.get_exports("other") == {"answer": 42}


# ---- 弃用钩子告警 ----


def test_overriding_deprecated_hook_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="qingci-bot.sdk"):

        class _Legacy(PluginBase):
            name = "legacy"

            async def on_load(self):
                return None

            async def on_unload(self):
                return None

            async def on_message(self, ctx):  # 已弃用
                return None

    messages = [r.message for r in caplog.records]
    assert any("on_message" in m and "弃用" in m for m in messages), messages


def test_normal_subclass_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger="qingci-bot.sdk"):

        class _Modern(PluginBase):
            name = "modern"

            async def on_load(self):
                return None

            async def on_unload(self):
                return None

    assert not [r for r in caplog.records if "弃用" in r.message]


def test_require_list_is_isolated_per_subclass():
    class _A(PluginBase):
        name = "a"

        async def on_load(self):
            return None

        async def on_unload(self):
            return None

    class _B(PluginBase):
        name = "b"

        async def on_load(self):
            return None

        async def on_unload(self):
            return None

    _A.require.append("x")
    assert "x" not in _B.require


# ---- 中间件与页面注册 ----


def test_register_before_after_dedupes():
    plugin = _DummyPlugin()

    async def hook(matcher, ctx):
        return None

    plugin.register_before(hook)
    plugin.register_before(hook)
    plugin.register_after(hook)
    plugin.register_after(hook)
    assert plugin._before_handlers == [hook]
    assert plugin._after_handlers == [hook]


def test_register_page_with_explicit_static_dir():
    plugin = _DummyPlugin()
    plugin.register_page("标题", icon="★", static_dir="/tmp/web")
    assert plugin._pages[-1]["static_dir"] == "/tmp/web"


def test_register_page_autodetect_without_web_dir():
    """本测试模块同级没有 web/ 目录，static_dir 应保持空串"""
    plugin = _DummyPlugin()
    plugin.register_page("标题")
    assert plugin._pages[-1]["static_dir"] == ""
