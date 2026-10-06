# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "xlrd"]
# ///
"""
把「東華大學統計資料/在學人數統計表/」114-1 的 .xls，轉成整齊的 CSV。

用法：
  uv run work/etl_enrollment.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "東華大學統計資料" / "在學人數統計表" / "114-1在學生人數統計表1141020--網路公告-10035人.xls"
DST = ROOT / "work" / "enrollment_114-1.csv"

# 每個學制區塊在報表裡以「xx班 合計N」這種列開頭（碩士在職專班寫作「碩專班 合計3」）
BLOCK_MARKER = {
    "博士班 合計1": "博士班",
    "碩士班 合計2": "碩士班",
    "碩專班 合計3": "碩士在職專班",
    "學士班 合計4": "學士班",
}

COL_COLLEGE = 1
COL_DEPT_RAW = 2
COL_FEMALE = 5
COL_MALE = 6

# 原始報表第 20 列（博士班區塊）的系所名稱欄位是空的，照合併規則往上補會變成
# 「材料科學與工程學系」，但這一列其實是「物理學系」的「應用物理博士班一般組」
# （系所名稱寫在下一列，比資料晚了一列，屬於報表本身的錯誤），用標準資料核對後
# 確認：扣掉這列，材料科學與工程學系的博士生人數才會跟標準資料一致。
DEPT_RAW_OVERRIDE = {20: "物理學系"}


def clean_college(s: str) -> str:
    # 去掉括號裡的註記，例如「環境暨海洋學院(111更名 )」-> 「環境暨海洋學院」
    return re.sub(r"[（(][^）)]*[）)]", "", s).strip()


def clean_dept_raw(s: str) -> str:
    # 保留括號內容，只清掉括號內多出來的空白，例如「(109新增 )」-> 「(109新增)」
    s = re.sub(r"\s+([）)])", r"\1", s)
    return s.strip()


def main():
    raw = pd.read_excel(SRC, sheet_name=0, header=None)

    rows = []
    program = None
    college = None
    dept_raw = None

    for idx, r in raw.iloc[4:].iterrows():
        col0 = str(r[0]).strip() if pd.notna(r[0]) else ""

        if col0 in BLOCK_MARKER:
            program = BLOCK_MARKER[col0]
            continue
        if col0.startswith("備註"):
            break
        if program is None:
            continue

        if pd.notna(r[COL_COLLEGE]):
            college = str(r[COL_COLLEGE]).strip()
        if pd.notna(r[COL_DEPT_RAW]):
            dept_raw = str(r[COL_DEPT_RAW]).strip()
        if idx in DEPT_RAW_OVERRIDE:
            dept_raw = DEPT_RAW_OVERRIDE[idx]

        female = r[COL_FEMALE] if pd.notna(r[COL_FEMALE]) else 0
        male = r[COL_MALE] if pd.notna(r[COL_MALE]) else 0

        rows.append(dict(
            college=clean_college(college),
            dept_raw=clean_dept_raw(dept_raw),
            program_raw=program,
            female=int(female),
            male=int(male),
        ))

    df = pd.DataFrame(rows)
    # 同一系所、同一學制下的多個分組（例如化學系的「一般組」「國際組」）加總成一列
    agg = df.groupby(["college", "dept_raw", "program_raw"], as_index=False, sort=False)[["female", "male"]].sum()

    long = agg.melt(
        id_vars=["college", "dept_raw", "program_raw"],
        value_vars=["female", "male"],
        var_name="gender_key",
        value_name="count",
    )
    long["gender"] = long["gender_key"].map({"female": "女", "male": "男"})
    long = long[["college", "dept_raw", "program_raw", "gender", "count"]]

    DST.parent.mkdir(exist_ok=True)
    long.to_csv(DST, index=False, encoding="utf-8-sig")
    print(f"寫出 {len(long)} 列到 {DST}")


if __name__ == "__main__":
    main()
