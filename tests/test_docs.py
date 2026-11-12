# Copyright (C) 2026 Zhou Zhe (aka luoqingci)
# SPDX-License-Identifier: GPL-3.0-or-later

"""文档一致性测试 — 全部文档的代码块必须可解析、导入的符号必须真实存在

文档里的示例是用户复制的第一份代码，比源码更容易过时：
改个名字、删个导出，示例照旧写着，读者复制后才发现跑不通。
本测试把「文档示例」纳入测试范围，成本低、能挡住最常见的两类漂移：

1. 语法错误（示例改动时打错字）
2. 导入了 SDK 已不存在的符号（改名/删除后忘了同步文档）

覆盖范围：README.md 与 docs/ 下全部 .md 文档（README 拆分后内容
分布在 GETTING_STARTED / PLUGIN_GUIDE / API / PUBLISHING 等文件，
逐个文件校验与集中校验等价，且新增文档自动纳入）。
"""

import ast
import re
from pathlib import Path

import pytest

import qingci_plugin_sdk as sdk

_ROOT = Path(__file__).resolve().parent.parent
README = _ROOT / "README.md"
DOC_FILES = [README, *sorted((_ROOT / "docs").glob("*.md"))]

_PY_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _code_blocks() -> list[tuple[str, str]]:
    """(文档相对路径, python 代码块) 列表"""
    result: list[tuple[str, str]] = []
    for path in DOC_FILES:
        rel = path.relative_to(_ROOT).as_posix()
        for block in _PY_BLOCK.findall(path.read_text(encoding="utf-8")):
            result.append((rel, block))
    return result


def _doc_text() -> str:
    """全部文档的拼接文本（导出符号可见性按全量文档校验）"""
    return "\n".join(p.read_text(encoding="utf-8") for p in DOC_FILES)


def test_docs_have_python_examples():
    """兜底：全部文档合计必须含 python 示例，README 自身必须有极简示例"""
    assert len(_code_blocks()) >= 10, "文档 python 示例总数异常（可能文件路径变更导致测试空转）"
    readme_blocks = _PY_BLOCK.findall(README.read_text(encoding="utf-8"))
    assert readme_blocks, "README 是唯一门面，必须保留至少一个可复制的极简示例"


@pytest.mark.parametrize("index", range(len(_code_blocks())))
def test_doc_block_parses(index: int):
    """每个 python 代码块都必须是合法 Python"""
    rel, block = _code_blocks()[index]
    try:
        ast.parse(block)
    except SyntaxError as e:  # pragma: no cover - 失败时给出定位
        raise AssertionError(f"{rel} 第 {index + 1} 个 python 代码块语法错误: {e.msg}") from e


def test_doc_imports_exist():
    """代码块中 `from qingci_plugin_sdk import X` 的 X 必须真实存在于包命名空间"""
    missing: list[str] = []
    for i, (rel, block) in enumerate(_code_blocks(), 1):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue  # 由 test_doc_block_parses 负责报错
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not node.module or not node.module.startswith("qingci_plugin_sdk"):
                continue
            for alias in node.names:
                if alias.name != "*" and not hasattr(sdk, alias.name):
                    missing.append(f"{rel} 代码块#{i}: from {node.module} import {alias.name}")
    assert not missing, "文档引用了不存在的符号：\n" + "\n".join(missing)


def test_docs_document_every_package_export():
    """包级 __all__ 的每个符号都应在文档中出现至少一次

    不要求出现在导入清单里（清单是常用子集），但整个文档都没提到，
    说明该能力对用户不可见。
    """
    text = _doc_text()
    undocumented = [name for name in sdk.__all__ if name not in text and name != "__version__"]
    assert not undocumented, f"文档未提及的导出符号：{undocumented}"


_EXPORT_COUNT = re.compile(r"__all__`?（当前 (\d+) 项）")


def test_doc_export_count_matches():
    """文档里写死的导出项数必须与实际 __all__ 一致

    这个数字最容易被忘掉：每次新增导出都会让它变成谎话，而读者没有理由怀疑它。
    """
    matched = _EXPORT_COUNT.findall(_doc_text())
    assert matched, "文档里找不到「（当前 N 项）」的导出项数说明（正则失配会导致本测试空转）"
    for stated in matched:
        assert int(stated) == len(sdk.__all__), (
            f"文档写着 __all__ 有 {stated} 项，实际 {len(sdk.__all__)} 项"
        )
