"""Hello World 示例插件

使用方式:
    cd Plugins-SDK
    uv pip install -e .
    python -c "from qingci_plugin_sdk import PluginBase; print('SDK OK')"

开发完成后，将 hello/ 目录复制到 Qingci-Bot/plugins/ 即可加载。
"""

from qingci_plugin_sdk import PluginBase, on_command, MatcherContext


class HelloPlugin(PluginBase):
    name = "hello"
    version = "1.0.0"
    author = "YourName"
    description = "Hello World 示例插件"

    async def on_load(self):
        self.matchers.append(
            on_command("hello", description="打个招呼")(self._handle_hello)
        )

    async def on_unload(self):
        pass

    async def _handle_hello(self, ctx: MatcherContext) -> str:
        return f"Hello, {ctx.sender_name or ctx.user_id}!"