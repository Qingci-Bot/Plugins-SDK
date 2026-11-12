# 发布与常见问题

> 把开发完成的插件放进主项目运行、发布流程，以及最常见的排障问答。

## 发布插件

开发完成后，把插件目录复制到主项目 **Qingci-Bot-CE** 的插件目录即可（源码运行时为 `Qingci-Bot-CE/plugins/`；实例模式下为 `Qingci-Bot-CE/instances/<name>/plugins/`，下例以 `default` 实例为例）：

```bash
# Windows
xcopy /E /I plugins\my_plugin ..\Qingci-Bot-CE\instances\default\plugins\my_plugin

# Mac / Linux
cp -r plugins/my_plugin ../Qingci-Bot-CE/instances/default/plugins/
```

重启 Bot 或通过 Web UI 插件管理页热重载，插件就会生效。

---

---

## 常见问题

### Q: 我改了代码，但 Bot 没变化？

A: 需要重启 Bot 或在 Web UI 的「插件管理」页点击「重载」。只改文件不会自动生效。

### Q: 插件加载报错 "PluginBase subclass not found"？

A: 检查你的类名是否和目录名一致（不是必须，但建议），以及是否继承了 `PluginBase`，且插件类直接定义在 `__init__.py` 中。

### Q: `self.scheduler` 或 `self.tool_registry` 是 None？

A: 这些是可选依赖，取决于主项目的配置。使用前务必判空：`if self.scheduler is not None:`。

### Q: 有类型提示吗？编辑器提示 `ctx.session` 可能为 None？

A: 有。SDK 自带 `py.typed`（PEP 561），安装后 mypy / Pylance / PyCharm 可直接获得类型信息。
`ctx.session` 的类型是 `Session | None`——只有宿主调度注入时才非空，所以使用前判空即可
（模板与本文档示例都这么写）。`Session` 上的自定义跨轮属性（`ctx.session.step = ...`）
按 `Any` 处理，不会报类型错误。

### Q: 如何调试插件？

A: 在代码里加 `logger.info(...)` 打印日志，然后在 Qingci-Bot 的 Web UI「运行日志」页面查看输出（需 `log.run_log_enabled` 开启，默认开）。

### Q: 可以导入第三方库吗？

A: 可以。在插件目录放置 `requirements.txt`（或在 `plugin.json` 的 `requirements` 字段）声明依赖，主项目加载插件时会自动安装到实例隔离的每插件独立目录（`data_root()/deps/<插件名>/`）并注入 `sys.path`，插件内可直接 `import`。该自动安装由主项目 `config.yaml` 的 `bot.auto_install_plugin_deps` 控制（默认开启，可关闭以降低供给链风险）。建议尽量使用 SDK 提供的能力，减少外部依赖。

> 注意区分：`requirements` 声明 **Python 包依赖**（自动安装）；类属性 `require` 声明**插件间依赖**（加载顺序与版本约束），两者不同。

### Q: 模板目录 `_template/` 会被加载吗？

A: 不会。以 `_` 开头的目录会被自动跳过。你可以放心保留它作为参考。

### Q: 多个插件能同时响应同一条消息吗？

A: 取决于 `block` 参数。`block=True`（默认）的匹配器匹配后，后续匹配器不再执行。`block=False` 则继续。

---
