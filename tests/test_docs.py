"""文档一致性测试 — README 代码块必须可解析、导入的符号必须真实存在

文档里的示例是用户复制的第一份代码，比源码更容易过时：
改个名字、删个导出，示例照旧写着，读者复制后才发现跑不通。
本测试把「文档示例」纳入测试范围，成本低、能挡住最常见的两类漂移：

1. 语法错误（示例改动时打错字）
2. 导入了 SDK 已不存在的符号（改名/删除后忘了同步文档）
"""

import ast
import re
from pathlib import Path

import pytest

import qingci_plugin_sdk as sdk

README = Path(__file__).resolve().parent.parent / "README.md"

_PY_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _code_blocks() -> list[str]:
    return _PY_BLOCK.findall(README.read_text(encoding="utf-8"))


def test_readme_has_python_examples():
    """兜底：README 必须含 python 示例（防止正则/文件路径变更导致测试空转）"""
    assert len(_code_blocks()) >= 10


@pytest.mark.parametrize("index", range(len(_code_blocks())))
def test_readme_block_parses(index: int):
    """每个 python 代码块都必须是合法 Python"""
    block = _code_blocks()[index]
    try:
        ast.parse(block)
    except SyntaxError as e:  # pragma: no cover - 失败时给出定位
        raise AssertionError(f"README 第 {index + 1} 个 python 代码块语法错误: {e.msg}") from e


def test_readme_imports_exist():
    """代码块中 `from qingci_plugin_sdk import X` 的 X 必须真实存在于包命名空间"""
    missing: list[str] = []
    for i, block in enumerate(_code_blocks(), 1):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue  # 由 test_readme_block_parses 负责报错
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not node.module or not node.module.startswith("qingci_plugin_sdk"):
                continue
            for alias in node.names:
                if alias.name != "*" and not hasattr(sdk, alias.name):
                    missing.append(f"代码块#{i}: from {node.module} import {alias.name}")
    assert not missing, "README 引用了不存在的符号：\n" + "\n".join(missing)


def test_readme_documents_every_package_export():
    """包级 __all__ 的每个符号都应在 README 中出现至少一次

    不要求出现在导入清单里（清单是常用子集），但整个 README 都没提到，
    说明该能力对用户不可见。
    """
    text = README.read_text(encoding="utf-8")
    undocumented = [name for name in sdk.__all__ if name not in text and name != "__version__"]
    assert not undocumented, f"README 未提及的导出符号：{undocumented}"


_EXPORT_COUNT = re.compile(r"__all__`?（当前 (\d+) 项）")


def test_readme_export_count_matches():
    """README 里写死的导出项数必须与实际 __all__ 一致

    这个数字最容易被忘掉：每次新增导出都会让它变成谎话，而读者没有理由怀疑它。
    """
    matched = _EXPORT_COUNT.findall(README.read_text(encoding="utf-8"))
    assert matched, "README 里找不到「（当前 N 项）」的导出项数说明（正则失配会导致本测试空转）"
    for stated in matched:
        assert int(stated) == len(sdk.__all__), (
            f"README 写着 __all__ 有 {stated} 项，实际 {len(sdk.__all__)} 项"
        )
