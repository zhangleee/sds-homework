# -*- coding: utf-8 -*-
"""一键复现：按顺序运行 01~05 全部流水线。

用法：
    python run_all.py
输出：data/clean/*.csv、outputs/tables/*.csv、outputs/figures/*.png、dashboard.html。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["01_load.py", "02_clean.py", "03_analysis.py", "04_visuals.py", "05_dashboard.py"]


def main() -> int:
    for name in SCRIPTS:
        path = os.path.join(ROOT, "scripts", name)
        print(f"\n===== 运行 {name} =====", flush=True)
        r = subprocess.run([sys.executable, path], cwd=ROOT)
        if r.returncode != 0:
            print(f"[run_all] {name} 失败，退出码 {r.returncode}", flush=True)
            return r.returncode
    print("\n[run_all] 全部步骤完成。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
