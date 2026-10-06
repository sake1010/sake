# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""
把 data/ 裡的三份標準 CSV（在學人數、休學人數、系所對照表），整理成
docs/data.js 給靜態網頁（雙擊開啟，不需伺服器）直接用 <script> 載入。

用法：
  uv run work/build_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "data.js"


def build_enrollment():
    df = pd.read_csv(DATA / "enrollment.csv", encoding="utf-8-sig")
    g = (
        df.groupby(["semester", "college", "dept", "degree", "gender"], as_index=False)["count"]
        .sum()
    )
    return g.to_dict(orient="records")


def build_leave():
    df = pd.read_csv(DATA / "leave.csv", encoding="utf-8-sig")
    g = (
        df.groupby(["semester", "college", "dept", "degree", "gender", "reason"], as_index=False)[
            ["new_leave", "on_leave_end"]
        ].sum()
    )
    return g.to_dict(orient="records")


def build_dept_aliases():
    df = pd.read_csv(DATA / "dept_mapping.csv", encoding="utf-8-sig")
    aliases = {}
    for _, r in df.iterrows():
        if pd.notna(r["aliases"]) and str(r["aliases"]).strip():
            aliases[r["dept"]] = [a for a in str(r["aliases"]).split(";") if a]
    return aliases


def main():
    payload = {
        "enrollment": build_enrollment(),
        "leave": build_leave(),
        "deptAliases": build_dept_aliases(),
    }
    OUT.parent.mkdir(exist_ok=True)
    js = "window.BI_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    OUT.write_text(js, encoding="utf-8")

    enroll_114_1 = sum(r["count"] for r in payload["enrollment"] if r["semester"] == "114-1")
    print(f"寫出 {OUT}（{OUT.stat().st_size:,} bytes）")
    print(f"enrollment {len(payload['enrollment'])} 列，leave {len(payload['leave'])} 列，deptAliases {len(payload['deptAliases'])} 個系所有舊名")
    print(f"核對：114-1 在學人數合計 = {enroll_114_1}（應為 10035）")


if __name__ == "__main__":
    main()
