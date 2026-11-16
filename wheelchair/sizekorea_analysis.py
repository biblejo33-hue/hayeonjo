# -*- coding: utf-8 -*-
"""
사이즈코리아 원자료(직접측정) → 신장 168~172cm 집단 추출 → 성별·연령대별 표본 수, 평균, SD, P5/P50/P95
결과: out/sizekorea_170_summary.csv, anthropometry_sizekorea.json (wc_model 이 자동으로 읽어 [공식 측정값] 으로 교체)

사용 예)
  python sizekorea_analysis.py  8차_직접측정_원자료.xlsx  --sex all --age 20-69
  python sizekorea_analysis.py  data.csv --sex 남 --height-col 키

※ 원자료 파일의 열 이름은 조사 차수마다 다를 수 있습니다. 아래 ITEMS 의 별칭 목록과 일치하지 않으면
  --map "앉은키=Sitting height" 처럼 직접 지정하세요.
※ 백분위수: numpy.percentile(method='linear') — 표본 수가 30 미만인 셀은 '참고용'으로 표시합니다.
"""
import argparse
import json
import os
import sys

import numpy as np

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas 가 필요합니다: pip install pandas openpyxl")

# 공식 항목명 : [원자료에서 찾을 별칭들]
ITEMS = {
    "키": ["키", "신장", "Stature"],
    "앉은키": ["앉은키", "Sitting height"],
    "앉은눈높이": ["앉은눈높이"],
    "앉은목뒤높이": ["앉은목뒤높이"],
    "앉은어깨높이": ["앉은어깨높이"],
    "앉은팔꿈치높이": ["앉은팔꿈치높이"],
    "앉은넙다리높이": ["앉은넙다리높이"],
    "앉은무릎높이": ["앉은무릎높이"],
    "앉은오금높이": ["앉은오금높이"],
    "앉은엉덩이너비": ["앉은엉덩이너비"],
    "앉은엉덩이오금수평길이": ["앉은엉덩이오금수평길이", "엉덩이오금수평길이"],
    "앉은엉덩이무릎수평길이": ["앉은엉덩이무릎수평길이", "엉덩이무릎수평길이"],
    "어깨너비": ["어깨너비"],
    "어깨최대너비": ["어깨최대너비"],
    "앉은팔꿈치사이너비": ["앉은팔꿈치사이너비", "팔꿈치사이너비"],
    "팔꿈치손목길이": ["팔꿈치손목길이", "아래팔길이"],
    "발길이": ["발길이"],
    "발너비": ["발너비"],
    "머리너비": ["머리너비"],
    "머리길이": ["머리길이"],
    "머리수직길이": ["머리수직길이"],
    "머리둘레": ["머리둘레"],
    "목둘레": ["목둘레"],
}
# wc_model 로 넘길 값: (모델 키, 항목, 통계)
TO_MODEL = [
    ("앉은키", "앉은키", "P50"), ("앉은눈높이", "앉은눈높이", "P50"),
    ("앉은어깨높이", "앉은어깨높이", "P50"), ("앉은팔꿈치높이", "앉은팔꿈치높이", "P50"),
    ("앉은넙다리높이", "앉은넙다리높이", "P50"), ("앉은무릎높이", "앉은무릎높이", "P50"),
    ("앉은오금높이", "앉은오금높이", "P50"), ("앉은오금높이_P5", "앉은오금높이", "P5"),
    ("앉은엉덩이너비", "앉은엉덩이너비", "P50"), ("앉은엉덩이너비_P95", "앉은엉덩이너비", "P95"),
    ("앉은엉덩이오금수평길이", "앉은엉덩이오금수평길이", "P50"),
    ("앉은엉덩이오금수평길이_P5", "앉은엉덩이오금수평길이", "P5"),
    ("앉은엉덩이무릎수평길이", "앉은엉덩이무릎수평길이", "P50"),
    ("어깨너비", "어깨너비", "P50"), ("어깨최대너비", "어깨최대너비", "P50"),
    ("앉은팔꿈치사이너비", "앉은팔꿈치사이너비", "P50"), ("팔꿈치손목길이", "팔꿈치손목길이", "P50"),
    ("발길이", "발길이", "P50"), ("발너비", "발너비", "P50"),
    ("머리너비", "머리너비", "P50"), ("머리길이", "머리길이", "P50"), ("머리수직길이", "머리수직길이", "P50"),
]


def find_col(cols, aliases):
    norm = {str(c).replace(" ", ""): c for c in cols}
    for a in aliases:
        a2 = a.replace(" ", "")
        if a2 in norm:
            return norm[a2]
    for a in aliases:                      # 부분 일치 (예: '앉은키(mm)')
        for k, c in norm.items():
            if k.startswith(a.replace(" ", "")):
                return c
    return None


def to_mm(s):
    s = pd.to_numeric(s, errors="coerce")
    med = s.median()
    return s * 10 if med is not None and med < 300 and med > 10 else s  # cm 로 기록된 경우 추정 변환


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--sheet", default=0)
    ap.add_argument("--hmin", type=float, default=1680)
    ap.add_argument("--hmax", type=float, default=1720)
    ap.add_argument("--sex", default="all", help="all | 남 | 여")
    ap.add_argument("--age", default="20-69")
    ap.add_argument("--sex-col", default=None)
    ap.add_argument("--age-col", default=None)
    ap.add_argument("--height-col", default=None)
    ap.add_argument("--map", action="append", default=[], help="공식항목=원자료열이름")
    ap.add_argument("--source", default="사이즈코리아 제8차 한국인 인체치수조사 직접측정 원자료")
    ap.add_argument("--year", default="2020-2024")
    ap.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    df = pd.read_csv(a.file, encoding_errors="ignore") if a.file.lower().endswith(".csv") \
        else pd.read_excel(a.file, sheet_name=a.sheet)
    cols = list(df.columns)
    mapping = {k: find_col(cols, v) for k, v in ITEMS.items()}
    for m in a.map:
        k, c = m.split("=", 1); mapping[k] = c
    if a.height_col:
        mapping["키"] = a.height_col
    sex_col = a.sex_col or find_col(cols, ["성별", "Sex", "Gender"])
    age_col = a.age_col or find_col(cols, ["나이", "만나이", "연령", "Age"])
    if mapping["키"] is None or sex_col is None or age_col is None:
        sys.exit("키/성별/나이 열을 찾지 못했습니다. --height-col --sex-col --age-col 로 지정하세요.\n열: %s" % cols)

    df["_H"] = to_mm(df[mapping["키"]])
    df["_age"] = pd.to_numeric(df[age_col], errors="coerce")
    df["_sex"] = df[sex_col].astype(str).str.strip().replace({"1": "남", "2": "여", "M": "남", "F": "여",
                                                              "남자": "남", "여자": "여"})
    lo, hi = [int(x) for x in a.age.split("-")]
    sub = df[(df["_H"] >= a.hmin) & (df["_H"] <= a.hmax) & (df["_age"] >= lo) & (df["_age"] <= hi)].copy()
    if a.sex != "all":
        sub = sub[sub["_sex"] == a.sex]
    sub["_ageband"] = (sub["_age"] // 10 * 10).astype(int).astype(str) + "대"

    rows = []
    groups = [("전체", sub)] + [("성별=" + s, g) for s, g in sub.groupby("_sex")] + \
             [("성별=%s,연령=%s" % k, g) for k, g in sub.groupby(["_sex", "_ageband"])]
    for item, col in mapping.items():
        if col is None:
            rows.append({"항목": item, "집단": "-", "n": 0, "비고": "원자료에 없음"})
            continue
        for gname, g in groups:
            x = to_mm(g[col]).dropna().values
            if len(x) == 0:
                continue
            p5, p50, p95 = np.percentile(x, [5, 50, 95], method="linear")
            rows.append({"항목": item, "원자료열": col, "집단": gname, "n": len(x),
                         "평균": round(x.mean(), 1), "SD": round(x.std(ddof=1), 1) if len(x) > 1 else None,
                         "P5": round(p5, 1), "P50": round(p50, 1), "P95": round(p95, 1),
                         "비고": "n<30 참고용" if len(x) < 30 else ""})
    out = pd.DataFrame(rows)
    here = a.outdir
    os.makedirs(os.path.join(here, "out"), exist_ok=True)
    out.to_csv(os.path.join(here, "out", "sizekorea_170_summary.csv"), index=False, encoding="utf-8-sig")

    cond = "신장 %d~%d mm, 연령 %s, 성별 %s" % (a.hmin, a.hmax, a.age, a.sex)
    vals = {}
    allrows = out[out["집단"] == "전체"].set_index("항목") if len(out) else None
    for key, item, stat in TO_MODEL:
        if allrows is not None and item in allrows.index and stat in allrows.columns:
            v = allrows.loc[item, stat]
            if v == v:
                vals[key] = {"value": float(v), "note": "%s %s (n=%d) %s %s" %
                             (item, stat, int(allrows.loc[item, "n"]), cond, a.source)}
    meta = {"source": a.source, "year": a.year, "condition": cond, "unit": "mm",
            "method": "numpy.percentile linear; mean/SD(ddof=1)", "values": vals}
    with open(os.path.join(here, "anthropometry_sizekorea.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(out.to_string(max_rows=80))
    print("\n→ anthropometry_sizekorea.json 저장 (%d개 값). export_and_render.py 또는 Rhino 스크립트를 다시 실행하세요."
          % len(vals))


if __name__ == "__main__":
    main()
