"""插件基类 — 插件 SDK 独立版本"""

import enum
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .context import MessageContext

if TYPE_CHECKING:
    from .matcher import Matcher


class PluginStatus(str, enum.Enum):
    """插件状态枚举"""

    LOADING = "loading"  # 正在加载（on_load 执行中）
    LOADED = "loaded"  # 已加载，正常运行
    DISABLED = "disabled"  # 已禁用，跳过事件分发
    ERROR = "error"  # 加载/运行出错
    UNLOADING = "unloading"  # 正在卸载（on_unload 执行中）


class PluginBase(ABC):
    """插件基类

    支持两种消息处理方式：
    1. 旧式：重写 on_message(ctx) -> str | None
    2. 新式：在 on_load 中注册 Matcher（self.matchers.append(on_command(...)(handler))）
       或用模块级装饰器 @on_command(...)（PluginManager 自动收集）

    新旧方式可共存，Dispatcher 按优先级统一调度。

    插件级配置：
    - 定义 Config 内嵌类（pydantic BaseModel 风格）声明配置项
    - 框架自动从 config.yaml 的 plugins.<name> 节加载到 self.plugin_config

    插件导出：
    - on_load 中调用 self.export("key", value) 暴露接口
    - 依赖方通过 self.get_exports("plugin_name") 获取导出字典

    状态/生命周期：
    - LOADING → LOADED → DISABLED ↔ LOADED → UNLOADING
    - LOADING → ERROR（加载失败）
    - 禁用/启用不触发 on_load/on_unload
    """

    # 插件元信息
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    category: str = ""  # 插件分类：chat / admin / tool / fun / 自定义
    # 依赖的插件 name 列表：支持 PEP 440 版本约束，如 "chat>=1.0,<2.0"
    # 依赖缺失或形成循环依赖时插件加载失败（借鉴 NoneBot2 require 机制）
    require: list[str] = []

    # 插件状态（由 PluginManager 管理）
    _status: PluginStatus = PluginStatus.LOADING

    # 依赖引用（由框架注入）
    bot: object | None = None
    db: object | None = None
    config: object | None = None
    connection: object | None = None
    llm: object | None = None
    scheduler: Any | None = None
    tool_registry: Any | None = None
    knowledge_store: Any | None = None
    session_state: Any | None = None  # TTL 会话状态存储
    event_bus: Any | None = None  # 跨插件事件总线（发布-订阅）

    # Matcher 列表
    matchers: list["Matcher"] | None = None

    # 插件级配置（由 PluginManager 从 config.yaml 加载）
    plugin_config: Any | None = None

    # 导出注册表（插件间服务接口）
    _exports: dict[str, Any]

    # Web 管理页面注册
    _pages: list[dict[str, str]]

    # Web API 注册（插件级 HTTP 接口，由主项目挂载到 /api/plugin-web/<name>/）
    _apis: list[dict[str, Any]]

    # 中间件链（per-handler 钩子）
    # before_handler: async (matcher, ctx) -> str | None
    #   - 返回非 None 时拦截，跳过 handler 并将返回值作为回复
    # after_handler: async (matcher, ctx, result) -> str | None
    #   - 可修改/替换 handler 返回值
    _before_handlers: list[Any]
    _after_handlers: list[Any]

    def __init__(self):
        self._exports = {}
        self._pages = []
        self._apis = []
        self._before_handlers = []
        self._after_handlers = []
        self._status = PluginStatus.LOADING
        # 国际化：插件可声明 i18n/<locale>.json 翻译资源，self._ = self.i18n.t。
        # 注意：加载时不会自动 load_dir；需插件在 on_load 手动调用
        # self.i18n.load_dir(self.data_dir / "i18n") 加载（宿主不代办）。
        from .i18n import I18n

        self.i18n = I18n("zh-CN")
        self._ = self.i18n.t

    # ---- 数据目录 ----

    @property
    def data_dir(self) -> Path:
        """插件专属数据目录（自动创建，建议用于持久化文件数据）

        路径约定：data_root()/plugins/<name>/；宿主卸载插件默认保留该目录，
        仅宿主「彻底删除（purge）」时删除，供插件存储运行时数据（缓存、导出文件等）。
        """
        from .paths import data_root

        d = data_root() / "plugins" / self.name
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- 状态 ----

    @property
    def status(self) -> PluginStatus:
        """插件当前状态"""
        return self._status

    @property
    def enabled(self) -> bool:
        """向后兼容：LOADED 视为启用（含 LOADING 过渡态）"""
        return self._status in (PluginStatus.LOADING, PluginStatus.LOADED)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """向后兼容：setter 由 PluginManager.disable/enable 使用"""
        if value:
            if self._status == PluginStatus.DISABLED:
                self._status = PluginStatus.LOADED
        else:
            if self._status == PluginStatus.LOADED:
                self._status = PluginStatus.DISABLED

    # ---- 导出机制 ----

    def export(self, key: str, value: Any) -> None:
        """导出接口供依赖方调用（在 on_load 中使用）"""
        self._exports[key] = value

    def get_exports(self, plugin_name: str) -> dict[str, Any]:
        """获取依赖插件的导出字典（需在 on_load 中声明 require）

        注意：方法名为 get_exports，避免与 require 依赖声明属性重名。
        """
        if self.bot is None:
            raise RuntimeError("插件未初始化，无法获取依赖")
        bot: Any = self.bot  # bot 由框架注入（类型为 object | None），运行时具备 plugin_manager
        dep = bot.plugin_manager.get(plugin_name)
        if dep is None:
            raise RuntimeError(f"依赖插件 {plugin_name} 未加载")
        return cast(dict[str, Any], dep._exports)

    # ---- 中间件 ----

    def register_before(self, fn) -> None:
        """注册 handler 前置钩子：async (matcher, ctx) -> str | None"""
        if fn not in self._before_handlers:
            self._before_handlers.append(fn)

    def register_after(self, fn) -> None:
        """注册 handler 后置钩子：async (matcher, ctx, result) -> str | None"""
        if fn not in self._after_handlers:
            self._after_handlers.append(fn)

    def register_page(self, title: str, icon: str = "◇", static_dir: str = "") -> None:
        """注册插件 Web 管理页面

        在 on_load 中调用，入口自动显示在插件管理页的插件卡片上。

        Args:
            title: 页面标题，显示在按钮上
            icon: 图标字符，默认 ◇
            static_dir: 静态文件目录的绝对路径。可省略，框架自动探测
                        插件 __init__.py 同级的 web/ 目录。
        """
        import os

        if not static_dir:
            # 自动探测：插件类所在模块同级的 web/ 目录
            module_file = getattr(type(self), "__module__", None)
            if module_file:
                import importlib
                import logging

                try:
                    mod = importlib.import_module(module_file)
                    mod_path = getattr(mod, "__file__", None)
                    if mod_path:
                        candidate = os.path.join(os.path.dirname(mod_path), "web")
                        if os.path.isdir(candidate):
                            static_dir = candidate
                except Exception as e:
                    # 探测失败记录日志，避免静默吞异常导致页面注册无 web/ 目录
                    logging.getLogger("qingci-bot.sdk").debug(
                        f"插件 web/ 目录探测失败: {module_file}: {e}"
                    )
        self._pages.append(
            {
                "title": title,
                "icon": icon,
                "static_dir": static_dir,
            }
        )

    def register_api(
        self,
        path: str,
        handler,
        *,
        methods: Sequence[str] | None = None,
        description: str = "",
    ) -> None:
        """注册插件 Web API（在 on_load 中调用）

        由主项目挂载到 `/api/plugin-web/<插件名>/<path>`，鉴权对齐主项目
        API 体系。插件可借此提供 WebUI 管理接口（配合 register_page 的
        前端页面使用）。

        handler 契约（任意平台实现均按此签名适配）：
            async def handler(request) -> Response | (data, status) | data
        - request：框架 HTTP 请求对象（主项目为 FastAPI Request，可读取
          `request.query_params` / `request.headers`、`await request.json()`
          取 JSON body、`await request.form()` 取上传文件等）
        - 返回 Response 对象（如 `JSONResponse` / `FileResponse`）时原样返回；
          返回 `(data, status_code)` 二元组时按 JSON 序列化并指定状态码；
          返回 dict / list / str 时自动 JSON 序列化

        Args:
            path: 相对路径（固定字面路径，不含 {id} 动态段；动态取值经
                  query 参数传递），如 "checkin-ranking"、"content-safety/terms/add"
            handler: 处理函数（见上方契约）
            methods: HTTP 方法列表，默认 ["GET"]
            description: 接口描述（调试/文档用）
        """
        self._apis.append(
            cast(
                dict,
                {
                    "path": str(path or "").strip("/"),
                    "handler": handler,
                    "methods": [str(m).upper() for m in (methods or ["GET"])],
                    "description": str(description or ""),
                },
            )
        )

    # ---- 生命周期 ----

    @abstractmethod
    async def on_load(self):
        """插件加载时调用"""
        ...

    @abstractmethod
    async def on_unload(self):
        """插件卸载时调用"""
        ...

    async def on_message(self, ctx: MessageContext) -> str | None:
        """处理消息事件，返回回复文本或 None（已弃用）

        Deprecated: 请改用 Matcher（on_message / on_command 等）注册消息处理。
        本回调保留仅为兼容旧插件，新插件请勿使用。
        """
        return None

    async def on_notice(self, event: dict) -> None:
        """处理通知事件（已弃用）

        Deprecated: 请改用 Matcher 工厂 on_notice()（matcher.py）注册事件处理。
        """
        return None

    async def on_request(self, event: dict) -> bool | None:
        """处理请求事件（加群/加好友），返回 True 同意 / False 拒绝 / None 忽略（已弃用）

        Deprecated: 请改用 Matcher 工厂 on_request()（matcher.py）注册事件处理。
        """
        return None

    async def on_disable(self):
        """插件被禁用时调用（可选覆写，用于停用定时任务等轻量清理）"""
        return None

    async def on_enable(self):
        """插件被启用时调用（可选覆写，用于恢复定时任务等）"""
        return None

    # ---- 全局生命周期钩子（可选覆写，默认空实现） ----

    async def on_startup(self):
        """Bot 启动完成后调用（所有插件加载完毕、连接就绪后）

        用于连接数据库、注册后台任务等耗时初始化。异常隔离，不影响启动。
        """
        return None

    async def on_shutdown(self):
        """Bot 停止时调用（在插件 on_unload 之前）

        用于释放 on_startup 中申请的资源。异常隔离。
        """
        return None

    async def on_bot_connect(self):
        """有 QQ 会话（LLBot）连接到反向 WebSocket 时调用

        初始连接与重连均触发，用于初始化会话相关资源。
        """
        return None

    async def on_metaevent(self, event: dict) -> bool | None:
        """处理元事件（生命周期，如 heartbeat / connect / enable）

        返回 True 表示已消费该事件（与 on_request 的审批语义对齐）。
        """
        return None
