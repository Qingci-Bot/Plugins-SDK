"""Plugins-SDK 冒烟测试 — 验证核心导出与基础行为（零外部依赖）

保证 SDK 作为独立包可安装、可导入，核心协议对象（PluginBase /
Matcher / Rule / MessageContext / 类型化事件 / i18n / llm_tool）
的基本行为正确，防止协议层回归。
"""

import qingci_plugin_sdk as sdk
from qingci_plugin_sdk import (
    EVERYONE,
    GroupIncreaseNotice,
    I18n,
    MessageContext,
    MessageEditedEvent,
    PluginBase,
    PluginStatus,
    llm_tool,
    on_command,
    on_startswith,
    parse_event,
    parse_notice_event,
    startswith,
)


def test_version():
    assert isinstance(sdk.__version__, str)
    parts = sdk.__version__.split(".")
    assert len(parts) >= 2
    assert all(p.isdigit() for p in parts)


def test_plugin_base_instantiation():
    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    assert p.name == "demo"
    assert p.status == PluginStatus.LOADING  # 初始过渡态
    assert p.enabled is True  # LOADING 视为启用（向后兼容）
    # LOADED → 禁用 → 恢复
    p._status = PluginStatus.LOADED
    p.enabled = False
    assert p.status == PluginStatus.DISABLED
    assert p.enabled is False
    p.enabled = True
    assert p.status == PluginStatus.LOADED


def test_register_api_records_registration():
    """register_api：规范化 path/methods 并写入 _apis（供主项目挂载）"""

    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    p.register_api("checkin-ranking", lambda req: {}, methods=["GET"], description="排行")
    p.register_api("/content-safety/terms/add", lambda req: {}, methods=["post"])
    p.register_api("raw", lambda req: {})

    assert len(p._apis) == 3
    first = p._apis[0]
    assert first["path"] == "checkin-ranking"  # 去除首尾斜杠
    assert first["methods"] == ["GET"]
    assert first["description"] == "排行"
    assert callable(first["handler"])
    # methods 大小写归一化；缺省为 GET
    assert p._apis[1]["methods"] == ["POST"]
    assert p._apis[1]["path"] == "content-safety/terms/add"
    assert p._apis[2]["methods"] == ["GET"]


def test_message_context_basics():
    ctx = MessageContext(
        message_type="group",
        user_id=100,
        group_id=200,
        raw_message="你好",
        sender={"nickname": "Alice", "card": ""},
    )
    assert ctx.sender_name == "Alice"
    assert ctx.platform == "onebot"  # 默认平台


def test_message_context_self_id_flat():
    """B1：扁平 self_id 优先读取"""
    ctx = MessageContext.from_v12_event(
        {
            "type": "message",
            "detail_type": "group",
            "self_id": "888",
            "message_id": "1",
            "message": [{"type": "text", "data": {"text": "hi"}}],
            "user_id": "123",
            "group_id": "456",
        }
    )
    assert ctx.self_id == "888"


def test_message_context_self_id_fallback_to_self_object():
    """B1：扁平 self_id 缺失时回退读 self.user_id（严格 v12 self 对象实现端）"""
    ctx = MessageContext.from_v12_event(
        {
            "type": "message",
            "detail_type": "group",
            "self": {"platform": "qq", "user_id": "777"},
            "message_id": "1",
            "message": [{"type": "text", "data": {"text": "hi"}}],
            "user_id": "123",
            "group_id": "456",
        }
    )
    assert ctx.self_id == "777"


async def test_startswith_rule_matches():
    rule = startswith("你好")
    ctx = MessageContext(raw_message="你好世界", plain_text="你好世界")
    assert await rule.check(None, {}, ctx) is True
    assert ctx.args == "世界"  # 前缀被去除写入 args


async def test_startswith_rule_rejects():
    rule = startswith("你好")
    ctx = MessageContext(raw_message="hello world", plain_text="hello world")
    assert await rule.check(None, {}, ctx) is False


async def test_startswith_rule_matches_with_leading_slash():
    """前缀规则剥离前导 `/`（与 command 对齐）：/你好世界 触发 startswith("你好")"""
    rule = startswith("你好")
    ctx = MessageContext(raw_message="/你好世界", plain_text="/你好世界")
    assert await rule.check(None, {}, ctx) is True
    assert ctx.args == "世界"


def test_on_startswith_builds_matcher():
    def handler(ctx):
        return "pong"

    matcher = on_startswith("ping")(handler)
    assert matcher.handler is handler
    assert matcher.event_type == "message"
    assert matcher.permission == EVERYONE
    assert matcher.block is True


def test_on_command_meta_aliases_and_hidden():
    """on_command 元信息：主命令名 + aliases + hidden_in_help（供宿主 /help 展示/过滤）"""

    def handler(ctx):
        return "ok"

    m = on_command("ping", aliases=("p", "pong"), description="测通", hidden_in_help=True)(handler)
    assert m.meta["command"] == "ping"
    assert m.meta["description"] == "测通"
    assert m.meta["aliases"] == ["p", "pong"]
    assert m.meta["hidden_in_help"] is True

    # 默认：无别名、可见
    m2 = on_command("help")(handler)
    assert m2.meta["aliases"] == []
    assert m2.meta["hidden_in_help"] is False


def test_parse_notice_group_increase():
    raw = {
        "post_type": "notice",
        "notice_type": "group_increase",
        "time": 1786889000,
        "self_id": 1,
        "user_id": 100,
        "group_id": 200,
        "sub_type": "approve",
    }
    ev = parse_notice_event(raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert ev.user_id == 100
    assert ev.group_id == 200
    assert ev.sub_type == "approve"


def test_parse_event_router():
    raw = {"post_type": "notice", "notice_type": "group_increase", "user_id": 1}
    ev = parse_event("notice", raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert parse_event("meta", raw) is None  # 未知类型返回 None


def test_parse_message_edited_event():
    """v12 message_edited → MessageEditedEvent（str/bool 字段类型化保留）"""
    raw = {
        "type": "notice",
        "detail_type": "message_edited",
        "sub_type": "friend",
        "id": "evt-7",
        "impl": "telegram",
        "platform": "telegram",
        "self_id": "30001",
        "time": 1786889000,
        "user_id": "10001",
        "group_id": "",
        "message_id": "42",
        "alt_message": "改后的内容",
        "message": [{"type": "text", "data": {"text": "改后的内容"}}],
        "is_at_bot": False,
    }
    ev = parse_notice_event(raw)
    assert isinstance(ev, MessageEditedEvent)
    assert ev.notice_type == "message_edited"
    assert ev.detail_type == "message_edited"
    assert ev.user_id == 10001
    assert ev.message_id == "42"  # str 字段原样保留（非 int）
    assert ev.alt_message == "改后的内容"
    assert ev.message[0]["type"] == "text"
    assert ev.is_at_bot is False  # bool 字段原样保留
    assert ev.platform == "telegram"


def test_parse_unknown_notice_falls_back_to_base():
    """未知 detail_type 仍回退 NoticeEvent 基类（不抛异常）"""
    raw = {"type": "notice", "detail_type": "group_message_react", "user_id": 1}
    ev = parse_notice_event(raw)
    assert type(ev).__name__ == "NoticeEvent"
    assert ev.notice_type == "group_message_react"  # 未知类型原样映射


def test_i18n_translate():
    i18n = I18n(translations={"hello": "你好"})
    assert i18n.t("hello") == "你好"
    assert i18n.t("missing") == "missing"  # 缺失 key 原样返回
    assert I18n(translations={"greet": "你好，{name}"}).t("greet", name="世界") == "你好，世界"


def test_llm_tool_decorator():
    @llm_tool(description="加法")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(1, 2) == 3  # 装饰器不改原函数行为
    from qingci_plugin_sdk.llm_tool import begin_tool_collection, end_tool_collection

    specs = begin_tool_collection()
    try:

        @llm_tool(description="乘法")
        def mul(a: int, b: int) -> int:
            return a * b

    finally:
        end_tool_collection()
    assert any(s.handler is mul for s in specs)
    assert any(s.description == "乘法" for s in specs)


def test_llm_tool_rejects_class_methods():
    """@llm_tool 仅用于模块级自由函数：类方法（qualname 含点且无 <locals>）拒绝收集"""
    import importlib

    llm_tool_module = importlib.import_module("qingci_plugin_sdk.llm_tool")

    def tool(self) -> str:  # noqa: ARG001 - 模拟类方法首参
        return "x"

    tool.__qualname__ = "SomeClass.tool"  # 模块层类方法形态（非局部函数）
    decorated = llm_tool_module.llm_tool(name="should_not_collect")(tool)

    llm_tool_module.begin_tool_collection()
    try:
        specs = [s for s in llm_tool_module._collector_stack[-1] if s.name == "should_not_collect"]
        assert specs == []
    finally:
        llm_tool_module.end_tool_collection()
    # 装饰器仍返回原函数，不影响类本身
    assert callable(decorated)


def test_require_isolated_between_plugins():
    """require 默认列表按插件类隔离，避免 self.require.append 污染其他插件"""

    class PluginA(PluginBase):
        name = "a"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    class PluginB(PluginBase):
        name = "b"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    a, b = PluginA(), PluginB()
    a.require.append("dep")
    assert PluginA.require == ["dep"]
    assert b.require == []
    assert PluginBase.require == []

    # 子类显式声明 require 时保持自己的列表，不受父类影响
    class PluginC(PluginA):
        name = "c"
        require = ["chat"]

    assert PluginC.require == ["chat"]
    assert PluginA.require == ["dep"]


def test_all_entries_are_importable():
    """__all__ 中的每个符号都必须真实存在于包命名空间（导出面一致性）"""
    assert [name for name in sdk.__all__ if not hasattr(sdk, name)] == []


def test_extended_notice_and_adapter_symbols_exported():
    """扩展通知类与适配器辅助函数必须走包级导出（CODING_STANDARDS §4）"""
    names = (
        "FriendPokeNotice",
        "GroupLuckyKingNotice",
        "GroupHonorChangeNotice",
        "GroupCardNotice",
        "GroupEssenceNotice",
        "GroupSignInNotice",
        "translate_v11_event",
        "parse_cq_string",
    )
    for name in names:
        assert name in sdk.__all__, name
        assert hasattr(sdk, name), name


def test_nested_tool_collection_keeps_outer_specs():
    """嵌套收集：内层 end 不丢弃外层已收集的 LLM 工具"""
    from qingci_plugin_sdk.llm_tool import begin_tool_collection, end_tool_collection

    outer = begin_tool_collection()
    try:

        @llm_tool(description="外层工具")
        def outer_tool() -> str:
            return "o"

        inner = begin_tool_collection()
        try:

            @llm_tool(description="内层工具")
            def inner_tool() -> str:
                return "i"

            assert [s.name for s in inner] == ["inner_tool"]
        finally:
            end_tool_collection()

        @llm_tool(description="外层工具 2")
        def outer_tool2() -> str:
            return "o2"

        assert [s.name for s in outer] == ["outer_tool", "outer_tool2"]
    finally:
        end_tool_collection()


def test_data_dir_cached_and_invalidated(tmp_path, monkeypatch):
    """data_dir 按 (数据根, 插件名) 缓存，避免每次访问都执行 mkdir"""
    from pathlib import Path as _Path

    from qingci_plugin_sdk import paths

    monkeypatch.setattr(paths, "data_root", lambda: tmp_path)

    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    mkdir_calls: list[_Path] = []
    real_mkdir = _Path.mkdir

    def counting_mkdir(self, *args, **kwargs):
        mkdir_calls.append(self)
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(_Path, "mkdir", counting_mkdir)

    p = DemoPlugin()
    first = p.data_dir
    # 首次访问需创建 plugins/ 与 plugins/<name>/（parents=True 会逐级调用）
    assert first == tmp_path / "plugins" / "demo"
    assert first.is_dir()
    first_calls = len(mkdir_calls)
    assert first_calls >= 1

    second = p.data_dir
    assert second == first
    assert len(mkdir_calls) == first_calls  # 第二次访问命中缓存，不再 mkdir

    # 宿主切换数据根（set_data_root）后缓存自动失效
    other = tmp_path / "other-root"
    other.mkdir(parents=True)
    monkeypatch.setattr(paths, "data_root", lambda: other)
    mkdir_calls.clear()
    assert p.data_dir == other / "plugins" / "demo"
    assert len(mkdir_calls) >= 1

    # 插件名变更同样失效（缓存键含插件名）
    p.name = "renamed"
    assert p.data_dir == other / "plugins" / "renamed"


def test_enabled_setter_ignores_invalid_transitions():
    """ERROR / UNLOADING 等状态下 enabled 赋值不改变状态（避免误复活）"""

    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    p._status = PluginStatus.ERROR
    p.enabled = True
    assert p.status == PluginStatus.ERROR
    p.enabled = False
    assert p.status == PluginStatus.ERROR


def test_middleware_registration_is_idempotent():
    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()

    async def before(matcher, ctx):
        return None

    async def after(matcher, ctx, result):
        return None

    p.register_before(before)
    p.register_before(before)
    p.register_after(after)
    p.register_after(after)
    assert p._before_handlers == [before]
    assert p._after_handlers == [after]


def test_register_page_records_static_dir(tmp_path):
    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    p.register_page("管理", icon="◆", static_dir=str(tmp_path))
    assert p._pages == [{"title": "管理", "icon": "◆", "static_dir": str(tmp_path)}]


def test_register_page_auto_detects_web_dir(tmp_path, monkeypatch):
    """未传 static_dir 时自动探测插件模块同级的 web/ 目录"""
    import importlib
    import types

    (tmp_path / "web").mkdir()
    fake_module = types.SimpleNamespace(__file__=str(tmp_path / "plugin.py"))
    monkeypatch.setattr(importlib, "import_module", lambda name: fake_module)

    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    p.register_page("管理")
    assert p._pages[-1]["static_dir"] == str(tmp_path / "web")


def test_get_exports_returns_dependency_exports():
    import types

    class DepPlugin(PluginBase):
        name = "dep"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    class HostPlugin(PluginBase):
        name = "host"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    dep = DepPlugin()
    dep.export("api", 42)
    host = HostPlugin()
    host.bot = types.SimpleNamespace(plugin_manager={"dep": dep})
    assert host.get_exports("dep") == {"api": 42}


def test_get_exports_raises_when_uninitialized():
    import pytest

    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    with pytest.raises(RuntimeError, match="未初始化"):
        DemoPlugin().get_exports("dep")


async def test_lifecycle_hooks_default_to_noop():
    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    assert await p.on_startup() is None
    assert await p.on_shutdown() is None
    assert await p.on_bot_connect() is None
    assert await p.on_metaevent({}) is None
    assert await p.on_disable() is None
    assert await p.on_enable() is None
    assert await p.on_message(MessageContext()) is None
    assert await p.on_notice({}) is None
    assert await p.on_request({}) is None


def test_py_typed_marker_present():
    """PEP 561：源码树与 wheel 都必须携带 py.typed"""
    from pathlib import Path

    assert (Path(sdk.__file__).parent / "py.typed").is_file()
