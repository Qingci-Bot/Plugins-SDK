"""插件基类 — 插件 SDK 独立版本"""

import enum
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .context import MessageContext

if TYPE_CHECKING:
    from .matcher import Matcher


# 已弃用的旧式事件钩子 → 推荐替代方式。
# 键必须与 PluginBase 上的方法名一致；覆写时在类创建阶段告警（见 __init_subclass__）。
_DEPRECATED_HOOKS: dict[str, str] = {
    "on_message": "Matcher 工厂 on_message()/on_command() 等",
    "on_notice": "Matcher 工厂 on_notice()（matcher.py）",
    "on_request": "Matcher 工厂 on_request()（matcher.py）",
}


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
    # 标注为 Any | None：这些对象由宿主实现，SDK 不依赖其类型（避免反向依赖），
    # 但用 object 会让下游插件的 self.bot.xxx / self.llm.chat() 在 mypy 下
    # 全部报「object 无该属性」。与下方 scheduler / tool_registry 等保持一致。
    bot: Any | None = None
    db: Any | None = None
    config: Any | None = None
    connection: Any | None = None
    llm: Any | None = None
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

    # data_dir 解析缓存：(数据根, 插件名) -> 已创建目录（避免每次访问都 mkdir）
    _data_dir_cache: tuple[tuple[str, str], Path] | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """为每个插件类隔离 require 列表，并对弃用钩子的覆写发出告警

        `require` 默认值是类级可变对象（list）。若子类未重新声明，多个插件
        会共享同一个列表，任一插件执行 `self.require.append(...)` 都会污染
        同进程其他插件。此处为未显式声明 require 的子类复制一份独立列表。

        弃用钩子（`on_message` / `on_notice` / `on_request`）仍保留默认空实现
        以兼容旧插件，但子类覆写时会在加载阶段记录 WARNING——否则插件作者
        得不到任何运行时信号，弃用状态会无限期延续下去。
        """
        super().__init_subclass__(**kwargs)
        if "require" not in cls.__dict__:
            cls.require = list(getattr(cls, "require", ()))

        for hook, replacement in _DEPRECATED_HOOKS.items():
            if hook in cls.__dict__:
                import logging

                logging.getLogger("qingci-bot.sdk").warning(
                    "插件 %s 覆写了已弃用的钩子 %s()，请改用 %s；"
                    "该钩子计划在下一个主版本（2.0）移除",
                    cls.__name__,
                    hook,
                    replacement,
                )

    def __init__(self):
        self._exports = {}
        self._pages = []
        self._apis = []
        self._before_handlers = []
        self._after_handlers = []
        self._status = PluginStatus.LOADING
        self._data_dir_cache = None
        # 国际化：插件可声明 i18n/<locale>.json 翻译资源，self._ = self.i18n.t。
        # 翻译文件放在**插件模块同级**的 i18n/ 目录（如 plugins/<name>/i18n/zh-CN.json），
        # 宿主加载插件时自动 load_dir 并应用全局语言（Qingci-Bot-CE 的
        # PluginManager._load_i18n → load_plugin_i18n），插件无需手动调用。
        # 独立开发（无宿主）时才需要自己 self.i18n.load_dir(<插件目录>)。
        from .i18n import I18n

        self.i18n = I18n("zh-CN")
        self._ = self.i18n.t

    # ---- 数据目录 ----

    @property
    def data_dir(self) -> Path:
        """插件专属数据目录（自动创建，建议用于持久化文件数据）

        路径约定：data_root()/plugins/<name>/；宿主卸载插件默认保留该目录，
        仅宿主「彻底删除（purge）」时删除，供插件存储运行时数据（缓存、导出文件等）。

        结果按 (数据根, 插件名) 缓存：mkdir 是系统调用，早期实现每次访问都执行
        一次（实测约 110µs），handler 内多次读取会显著拖慢消息处理。宿主通过
        set_data_root() 切换数据根或插件名变更时自动失效。
        """
        from .paths import data_root

        root = data_root()
        cache_key = (str(root), self.name)
        cached = self._data_dir_cache
        if cached is not None and cached[0] == cache_key:
            return cached[1]

        d = root / "plugins" / self.name
        d.mkdir(parents=True, exist_ok=True)
        self._data_dir_cache = (cache_key, d)
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

        旁路通知：宿主向每个覆写了本钩子的插件各调一次，**忽略返回值**——没有
        「消费掉、后续插件不再收到」的语义。返回 ``True`` 不会阻止其他插件收到，
        也不会影响事件分发。

        需要拦截事件用 Matcher 的 ``block``；需要审批加好友/加群用
        ``on_request`` 返回 ``bool``（那个返回值是真被消费的）。
        """
        return None
