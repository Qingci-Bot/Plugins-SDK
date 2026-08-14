"""插件级 LLM 工具声明（Function Calling）— 插件 SDK 独立版本

允许插件用装饰器直接注册 Function Calling 工具，构建「LLM 原生插件」生态。
工具在插件加载时注册到主项目全局 ToolRegistry，卸载时自动注销。

用法（模块级装饰器）：
    from qingci_plugin_sdk import llm_tool

    @llm_tool(description="查询城市天气")
    def get_weather(city: str = "北京") -> str:
        return f"{city}: 晴 25°C"

也可以显式声明标准 JSON Schema 参数：
    @llm_tool(
        name="sum",
        description="计算两个整数之和",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "integer", "description": "加数"},
                "b": {"type": "integer", "description": "加数"},
            },
            "required": ["a", "b"],
        },
    )
    def add(a: int, b: int) -> int:
        return a + b

工具注册名由主项目自动加插件名前缀（<plugin_name>_<tool_name>），避免跨插件冲突。
本 SDK 提供声明与收集机制；实际注册由主项目 PluginManager 完成。
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LlmToolSpec:
    """LLM 工具声明（插件加载时收集，注册到全局注册表）"""

    name: str
    handler: Any
    description: str = ""
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})


# 模块级工具收集栈：插件加载时设置，收集到的工具关联到当前插件
_tool_collector: Optional[list[LlmToolSpec]] = None
_tool_lock = threading.Lock()


def llm_tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[dict] = None,
):
    """声明插件级 LLM 工具（装饰器工厂）

    Args:
        name: 工具名（默认取函数名）
        description: 工具描述（供模型判断何时调用）
        parameters: 标准 JSON Schema 参数定义（缺省时为空对象）
    """

    def decorator(func):
        spec = LlmToolSpec(
            name=name or func.__name__,
            handler=func,
            description=description or (func.__doc__ or "").strip(),
            parameters=parameters or {"type": "object", "properties": {}},
        )
        with _tool_lock:
            if _tool_collector is not None:
                _tool_collector.append(spec)
        return func

    return decorator


def begin_tool_collection() -> list[LlmToolSpec]:
    """开始收集模块级 LLM 工具，返回收集列表"""
    global _tool_collector
    with _tool_lock:
        _tool_collector = []
        return _tool_collector


def end_tool_collection():
    """结束收集"""
    global _tool_collector
    with _tool_lock:
        _tool_collector = None