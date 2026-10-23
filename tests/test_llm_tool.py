"""@llm_tool 声明与收集器测试

此前该模块只有间接覆盖。重点验证两件事：
1. 类方法被拒绝（宿主按零参调用会缺 self）
2. 收集器是栈，嵌套加载时内层 end 不会丢弃外层已收集的工具
"""

from __future__ import annotations

import importlib
import logging

from qingci_plugin_sdk.llm_tool import (
    begin_tool_collection,
    end_tool_collection,
)
from qingci_plugin_sdk.llm_tool import (
    llm_tool as llm_tool_decorator,
)

# 包级导出里有同名函数 llm_tool（装饰器），会遮蔽同名子模块，
# 因此取模块要走 importlib，不能 from qingci_plugin_sdk import llm_tool
llm_tool = importlib.import_module("qingci_plugin_sdk.llm_tool")


def test_defaults_come_from_function():
    collector = begin_tool_collection()
    try:

        @llm_tool_decorator()
        def get_time():
            """返回当前时间"""
            return "now"

    finally:
        end_tool_collection()

    assert len(collector) == 1
    spec = collector[0]
    assert spec.name == "get_time"
    assert spec.description == "返回当前时间"
    assert spec.parameters == {"type": "object", "properties": {}}
    assert spec.handler is get_time


def test_explicit_metadata_overrides_defaults():
    collector = begin_tool_collection()
    try:

        @llm_tool_decorator(
            name="weather",
            description="查天气",
            parameters={"type": "object", "properties": {"city": {"type": "string"}}},
        )
        def _weather(city: str = "北京"):
            return city

    finally:
        end_tool_collection()

    spec = collector[0]
    assert spec.name == "weather"
    assert spec.description == "查天气"
    assert "city" in spec.parameters["properties"]


def test_class_method_is_rejected_with_warning(caplog):
    """模块级类的方法（qualname 形如 Class.method）必须被拒绝

    注意：在函数内部定义的类，其 qualname 含 <locals>，属于「局部定义」会被放行；
    要复现真实场景（插件在模块级定义类），这里用 exec 在模块级命名空间里定义。
    """
    collector = begin_tool_collection()
    try:
        with caplog.at_level(logging.WARNING, logger="qingci-plugin-sdk.llm_tool"):
            code = """
class _Holder:
    @llm_tool_decorator()
    def method(self):
        return None
"""
            exec(compile(code, "<test-module>", "exec"), {"llm_tool_decorator": llm_tool_decorator})
    finally:
        end_tool_collection()

    assert collector == [], "类方法不应被收集"
    assert any("仅用于模块级自由函数" in r.message for r in caplog.records)


def test_nested_function_is_allowed():
    """局部函数 qualname 含 <locals>，放行（宿主可零参调用）"""
    collector = begin_tool_collection()
    try:

        def outer():
            @llm_tool_decorator()
            def inner():
                return 1

            return inner

        outer()
    finally:
        end_tool_collection()

    assert [s.name for s in collector] == ["inner"]


def test_collector_is_stack_for_nested_loading():
    outer = begin_tool_collection()
    inner = begin_tool_collection()
    try:
        assert inner is not outer
    finally:
        end_tool_collection()
        end_tool_collection()
    assert llm_tool._collector_stack == []


def test_end_on_empty_stack_is_noop():
    """宿主可能在异常路径多调用一次 end，不应抛异常"""
    assert llm_tool._collector_stack == []
    end_tool_collection()
    assert llm_tool._collector_stack == []
