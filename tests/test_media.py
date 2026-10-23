"""媒体解析测试 — file_id → 模型可读取地址

覆盖三类输入：已可直接使用的（URL / data URI）、本地/内联的（文件、base64）、
需要走平台 API 的（不透明 file_id），以及各类失败降级。
"""

from __future__ import annotations

import base64

import pytest

from qingci_plugin_sdk.media import DEFAULT_MAX_BYTES, resolve_image, resolve_images

PNG_HEAD = b"\x89PNG\r\n\x1a\n"
JPEG_HEAD = b"\xff\xd8\xff"


class _Conn:
    """替身连接：按 action 返回预设响应，或抛出异常"""

    def __init__(self, responses: dict[str, dict | Exception]):
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    async def call_api(self, action: str, params: dict | None = None, timeout: float = 30):
        self.calls.append((action, params or {}))
        resp = self.responses.get(action)
        if isinstance(resp, Exception):
            raise resp
        if resp is None:
            raise RuntimeError(f"unsupported action {action}")
        return resp


# ---- 直接可用 / 空值 ----


@pytest.mark.parametrize(
    "ref",
    [
        "https://example.com/a.jpg",
        "http://example.com/a.jpg",
        "data:image/png;base64,iVBORw0KGgo=",
    ],
)
async def test_passthrough_refs_returned_unchanged(ref):
    assert await resolve_image(_Conn({}), ref) == ref


@pytest.mark.parametrize("ref", ["", "   ", None])
async def test_empty_ref_returns_none(ref):
    assert await resolve_image(_Conn({}), ref) is None


# ---- base64 / 本地文件 ----


async def test_base64_prefix_becomes_data_uri_with_sniffed_mime():
    ref = "base64://" + base64.b64encode(PNG_HEAD + b"payload").decode()
    out = await resolve_image(_Conn({}), ref)
    assert out is not None
    assert out.startswith("data:image/png;base64,")


async def test_base64_jpeg_mime_sniffed():
    ref = "base64://" + base64.b64encode(JPEG_HEAD + b"x").decode()
    out = await resolve_image(_Conn({}), ref)
    assert out is not None and out.startswith("data:image/jpeg;base64,")


async def test_local_file_becomes_data_uri(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(PNG_HEAD + b"data")
    out = await resolve_image(_Conn({}), str(img))
    assert out is not None and out.startswith("data:image/png;base64,")


async def test_oversized_local_file_is_skipped(tmp_path):
    img = tmp_path / "big.png"
    img.write_bytes(PNG_HEAD + b"0" * (DEFAULT_MAX_BYTES + 1))
    assert await resolve_image(_Conn({}), str(img)) is None


async def test_oversized_inline_base64_is_skipped():
    ref = "base64://" + base64.b64encode(b"0" * (DEFAULT_MAX_BYTES + 1)).decode()
    assert await resolve_image(_Conn({}), ref) is None


# ---- 平台 API ----


async def test_opaque_id_resolved_via_get_image_url():
    conn = _Conn({"get_image": {"url": "https://cdn.example.com/x.jpg"}})
    assert await resolve_image(conn, "ABC123") == "https://cdn.example.com/x.jpg"
    assert conn.calls[0][0] == "get_image"
    assert conn.calls[0][1] == {"file": "ABC123"}


async def test_falls_back_to_get_file_when_get_image_raises():
    conn = _Conn(
        {
            "get_image": RuntimeError("unsupported"),
            "get_file": {"url": "https://cdn.example.com/y.png"},
        }
    )
    assert await resolve_image(conn, "opaque") == "https://cdn.example.com/y.png"
    assert [c[0] for c in conn.calls] == ["get_image", "get_file"]


async def test_api_returning_base64_becomes_data_uri():
    payload = base64.b64encode(JPEG_HEAD + b"z").decode()
    conn = _Conn({"get_image": {"base64": payload}})
    out = await resolve_image(conn, "opaque")
    assert out is not None and out.startswith("data:image/jpeg;base64,")


async def test_api_returning_local_path_becomes_data_uri(tmp_path):
    img = tmp_path / "from_api.png"
    img.write_bytes(PNG_HEAD + b"q")
    conn = _Conn({"get_image": {"file": str(img)}})
    out = await resolve_image(conn, "opaque")
    assert out is not None and out.startswith("data:image/png;base64,")


async def test_unresolvable_id_returns_none():
    conn = _Conn({"get_image": {}, "get_file": {}})
    assert await resolve_image(conn, "opaque") is None


async def test_missing_connection_returns_none_for_opaque_id():
    assert await resolve_image(None, "opaque") is None


# ---- 批量 ----


async def test_resolve_images_skips_failures_and_keeps_order():
    conn = _Conn({"get_image": {"url": "https://cdn.example.com/ok.jpg"}})
    out = await resolve_images(conn, ["https://a/1.jpg", "opaque", ""], max_count=10)
    assert out == ["https://a/1.jpg", "https://cdn.example.com/ok.jpg"]


async def test_resolve_images_respects_max_count():
    conn = _Conn({})
    refs = [f"https://a/{i}.jpg" for i in range(5)]
    assert len(await resolve_images(conn, refs, max_count=2)) == 2


async def test_resolve_images_empty_input():
    assert await resolve_images(_Conn({}), []) == []
    assert await resolve_images(_Conn({}), None) == []
