"""I18n 国际化测试 — 翻译查找 / 占位符格式化 / 目录加载"""

from __future__ import annotations

import json

from qingci_plugin_sdk import I18n


def test_translate_hit_and_miss():
    i18n = I18n(translations={"hello": "你好"})
    assert i18n.t("hello") == "你好"
    assert i18n.t("missing") == "missing"  # 缺失 key 原样返回，不崩溃


def test_translate_formats_placeholders():
    i18n = I18n(translations={"greet": "你好，{name}"})
    assert i18n.t("greet", name="世界") == "你好，世界"
    # 无参数时不触发格式化（保留原始模板）
    assert i18n.t("greet") == "你好，{name}"


def test_translate_bad_placeholder_falls_back_to_template():
    i18n = I18n(translations={"bad": "缺少 {name}"})
    assert i18n.t("bad", other=1) == "缺少 {name}"


def test_call_alias():
    i18n = I18n(translations={"hello": "你好"})
    assert i18n("hello") == "你好"


def test_locale_property_and_setter():
    i18n = I18n("zh-CN")
    assert i18n.locale == "zh-CN"
    i18n.locale = "en-US"
    assert i18n.locale == "en-US"


def test_set_overrides_single_key():
    i18n = I18n()
    i18n.set("k", "v")
    assert i18n.t("k") == "v"


def test_load_dir_reads_locale_file(tmp_path):
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    (i18n_dir / "zh-CN.json").write_text(
        json.dumps({"hello": "你好，{name}"}, ensure_ascii=False), encoding="utf-8"
    )
    i18n = I18n("zh-CN")
    assert i18n.load_dir(tmp_path) is True
    assert i18n.t("hello", name="世界") == "你好，世界"


def test_load_dir_missing_file_returns_false(tmp_path):
    assert I18n().load_dir(tmp_path) is False


def test_load_dir_invalid_json_returns_false(tmp_path):
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    (i18n_dir / "zh-CN.json").write_text("{not json", encoding="utf-8")
    assert I18n().load_dir(tmp_path) is False


def test_load_dir_non_dict_payload_returns_false(tmp_path):
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    (i18n_dir / "zh-CN.json").write_text("[1, 2]", encoding="utf-8")
    assert I18n().load_dir(tmp_path) is False
