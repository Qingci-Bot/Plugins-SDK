"""媒体资源解析 — 把平台图片引用换成模型可读取的地址

各平台下发的图片引用通常是不透明 ID（OneBot 12 的 `file_id`、Telegram 的
`file_id`），大模型无法读取。本模块负责把它换成 `http(s)` URL 或 `data:` URI。

**零运行时依赖**：只用标准库，不引入 httpx 之类的 HTTP 客户端。因此这里只做
「解析」不做「下载」——远端 URL 直接返回，由模型侧拉取；只有平台 API 明确
返回 base64、或给出本地文件路径时，才在本地编码成 data URI。

典型用法（插件在调用 LLM 前）：

    from qingci_plugin_sdk import resolve_images

    images = await resolve_images(self.connection, ctx.images)
    reply = await self.llm.chat(message=ctx.plain_text, images=images or None)
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

__all__ = ["resolve_image", "resolve_images", "DEFAULT_MAX_BYTES"]

logger = logging.getLogger("qingci-bot.sdk.media")

# 单图默认上限 4 MiB：主流视觉模型单图限制多在 5–20 MB，
# 且 base64 编码会再膨胀约 4/3，留出余量。
DEFAULT_MAX_BYTES = 4 * 1024 * 1024

# 已可直接使用的前缀（无需解析）
_PASSTHROUGH_PREFIXES = ("http://", "https://", "data:")

_BASE64_PREFIX = "base64://"

# 魔数 → MIME（data URI 需要正确的类型，否则部分服务端会拒绝）
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
)


def _sniff_mime(data: bytes) -> str:
    """按魔数猜 MIME，猜不出按 PNG 处理（模型侧多数会自行纠正）"""
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _to_data_uri(data: bytes) -> str:
    return f"data:{_sniff_mime(data)};base64,{base64.b64encode(data).decode('ascii')}"


def _from_local_file(path: Path, max_bytes: int) -> str | None:
    """本地文件 → data URI（先看大小，避免把超大文件读进内存）"""
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size <= 0:
        return None
    if size > max_bytes:
        logger.warning("图片过大已跳过：%s（%d 字节 > 上限 %d）", path, size, max_bytes)
        return None
    try:
        return _to_data_uri(path.read_bytes())
    except OSError as e:
        logger.warning("读取本地图片失败：%s（%s）", path, e)
        return None


def _from_response(resp: dict[str, Any], max_bytes: int) -> str | None:
    """从平台 API 响应里提取可用地址

    兼容三种返回形态（不同实现端不一致）：
    - `url`：CDN 直链，直接可用
    - `base64`：内联数据
    - `file`：可能是本地路径、`base64://` 串或文件名
    """
    url = resp.get("url")
    if isinstance(url, str) and url.startswith(_PASSTHROUGH_PREFIXES):
        return url

    b64 = resp.get("base64")
    if isinstance(b64, str) and b64:
        raw = b64[len(_BASE64_PREFIX) :] if b64.startswith(_BASE64_PREFIX) else b64
        try:
            data = base64.b64decode(raw, validate=False)
        except (ValueError, TypeError):
            data = b""
        if data:
            if len(data) > max_bytes:
                logger.warning("图片过大已跳过：%d 字节 > 上限 %d", len(data), max_bytes)
                return None
            return _to_data_uri(data)

    file = resp.get("file")
    if isinstance(file, str) and file:
        if file.startswith(_PASSTHROUGH_PREFIXES):
            return file
        if file.startswith(_BASE64_PREFIX):
            return _from_response({"base64": file}, max_bytes)
        path = Path(file)
        if path.is_file():
            return _from_local_file(path, max_bytes)

    return None


async def resolve_image(
    connection: Any,
    ref: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: float = 15.0,
) -> str | None:
    """把一个图片引用解析为模型可读取的地址

    Args:
        connection: 宿主注入的 `self.connection`（提供 `call_api`）
        ref: 图片引用——可能是 URL、data URI、`base64://` 串、本地路径或不透明 file_id
        max_bytes: 本地编码时的字节上限（URL 直链不受此限制）
        timeout: 调用平台 API 的超时（秒）

    Returns:
        `http(s)` URL 或 `data:` URI；无法解析时返回 None（调用方应跳过该图）
    """
    ref = (ref or "").strip()
    if not ref:
        return None
    if ref.startswith(_PASSTHROUGH_PREFIXES):
        return ref

    # 本地路径（部分适配器直接下发文件路径）
    path = Path(ref)
    if path.is_file():
        return _from_local_file(path, max_bytes)

    if ref.startswith(_BASE64_PREFIX):
        return _from_response({"base64": ref}, max_bytes)

    if connection is None:
        return None

    # 平台 API：v11 用 get_image(file=...)，v12 用 get_file(file_id=...)
    for action, params in (
        ("get_image", {"file": ref}),
        ("get_file", {"file_id": ref}),
    ):
        try:
            resp = await connection.call_api(action, params, timeout=timeout)
        except Exception as e:  # noqa: BLE001 - 适配器实现差异大，统一降级
            logger.debug("调用 %s 失败（%s）：%s", action, ref, e)
            continue
        if not isinstance(resp, dict):
            continue
        resolved = _from_response(resp, max_bytes)
        if resolved:
            return resolved

    logger.warning("无法解析图片引用，已跳过：%s", ref)
    return None


async def resolve_images(
    connection: Any,
    refs: list[str] | None,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_count: int = 4,
    timeout: float = 15.0,
) -> list[str]:
    """批量解析，跳过无法解析的项

    Args:
        refs: 原始引用列表（通常是 `ctx.images`）
        max_count: 最多保留几张（视觉模型对图片数量通常有限制，也控制成本）
    """
    if not refs:
        return []
    if max_count > 0:
        refs = list(refs)[:max_count]
    out: list[str] = []
    for ref in refs:
        resolved = await resolve_image(connection, ref, max_bytes=max_bytes, timeout=timeout)
        if resolved:
            out.append(resolved)
    return out
