# Copyright (C) 2026 Zhou Zhe (aka luoqingci) and Qingci-Bot contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""版权声明契约：所有源码文件必须带 Copyright + SPDX 标识

复用 scripts/license_headers.py --check 作为唯一判定口径，
新增源码文件漏写声明时 CI 会直接失败。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_all_source_files_have_license_headers():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "license_headers.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
