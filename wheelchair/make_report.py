# -*- coding: utf-8 -*-
"""out/*.csv 와 wc_model 값으로 REPORT.md(A~H)를 생성합니다. export_and_render.py 실행 후 사용."""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wc_model as W  # noqa: E402

d, P, EXTRA = W.build_all(HERE)
OUT = os.path.join(HERE, "out")


def table(header, rows):
    s = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
    for r in rows:
        s += "| " + " | ".join("" if x is None else str(x) for x in r) + " |\n"
    return s


def fmt(v):
    return ("%.1f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


official_used = any(t == W.OFFICIAL for _, t, _ in W.ANTHRO.values())

A_ITEMS = [
    ("앉은키", "있음"), ("앉은어깨높이", "있음"), ("앉은팔꿈치높이", "있음"), ("앉은엉덩이너비", "있음"),
    ("앉은엉덩이오금수평길이", "있음"), ("앉은엉덩이무릎수평길이", "있음"), ("앉은오금높이", "있음"),
    ("앉은무릎높이", "있음"), ("앉은넙다리높이", "있음"), ("어깨너비", "있음"), ("발길이", "있음"),
    ("발너비", "있음"), ("머리너비", "있음"), ("머리길이", "확인 필요"), ("머리수직길이", "확인 필요"),
    ("앉은눈높이", "있음"), ("어깨최대너비", "확인 필요"), ("앉은팔꿈치사이너비", "확인 필요"),
    ("팔꿈치손목길이", "확인 필요"),
]

md = []
md.append("# 재활휠체어 1:1 기본 볼륨 모델 — 170cm 성인 기준 (Size Korea 연동형)\n")
md.append("> **현재 상태:** 사이즈코리아 원자료에 접근하지 못해(이 실행 환경에서 sizekorea.kats.go.kr 접속 차단) "
          "모든 인체치수는 **[임시 가정값]**입니다. 사이즈코리아 공식 수치가 아닙니다. "
          "원자료를 받아 `sizekorea_analysis.py`를 실행하면 값이 **[공식 측정값]**으로 교체되고 "
          "모델·도면·표가 다시 계산됩니다.\n" if not official_used else
          "> 인체치수 일부가 사이즈코리아 원자료 분석값([공식 측정값])으로 교체되었습니다.\n")
md.append("좌표계: 원점 = 바닥·차체 중심선·후륜 차축 아래, +X 전방, +Y 사용자 왼쪽, +Z 위. 단위 mm.\n")

# A
md.append("\n## A. 사이즈코리아 인체치수 분석표\n")
md.append("### A-1. 조사 대상 자료 및 접근 결과\n")
md.append(table(["자료", "상태", "필요 조치"], [
    ["제8차 한국인 인체치수조사(2020~2024) 성인 직접측정 원자료", "접근 불가(네트워크 차단)", "회원가입 → 자료 신청·승인 후 다운로드"],
    ["2024 휠체어 사용 척수손상 장애인 측정 자료", "접근 불가 — 존재·공개범위 미확인", "사이트 '자료실/인체치수 데이터' 에서 공개 여부 확인"],
    ["제8차 3D 표준인체형상", "접근 불가", "3D 형상 자료 신청 → OBJ/STL 등을 Rhino 'Human Reference' 레이어에 Import"],
]))
md.append("\n### A-2. 항목별 입력값 (모두 교체 대상)\n")
rows = []
for k, avail in A_ITEMS:
    val, tag, note = W.ANTHRO[k]
    rows.append([k, avail, fmt(val), "mm", "[%s]" % tag, note,
                 "제8차(2020~2024) 직접측정, 신장 1680~1720mm, 성별·연령 분리, numpy linear 백분위수" if tag == W.OFFICIAL
                 else "출처 없음 — 모델링용 자리표시값"])
for k in ("앉은엉덩이너비_P95", "앉은엉덩이오금수평길이_P5", "앉은오금높이_P5"):
    val, tag, note = W.ANTHRO[k]
    rows.append([k, "-", fmt(val), "mm", "[%s]" % tag, note, "출처 없음"])
md.append(table(["항목(사이즈코리아 명칭)", "원자료 수록", "값", "단위", "구분", "비고", "출처·조건·산출방법"], rows))
md.append("\n'원자료 수록' 열의 '확인 필요'는 해당 명칭이 8차 직접측정 항목표에 있는지 확인하지 못했다는 뜻입니다. "
          "목·머리 지지용 치수 중 **'앉은후두부높이' 같은 항목은 일반 측정항목에 없을 가능성이 높아** "
          "`앉은키 − 정수리~후두부 오프셋(110, 임시)`으로 대체했습니다.\n")
md.append("\n### A-3. 168~172cm 집단 남녀·연령별 비교 및 5·50·95백분위수\n")
md.append("원자료 없이 계산할 수 없어 **표를 비워 두었습니다.** 원자료를 받은 뒤 아래 명령을 실행하면 "
          "`out/sizekorea_170_summary.csv`에 항목 × (전체 / 성별 / 성별×연령대)별 n·평균·SD·P5·P50·P95가 생성됩니다. "
          "셀 표본이 30명 미만이면 '참고용'으로 표시합니다.\n")
md.append("```bash\npython sizekorea_analysis.py <다운로드한_원자료.xlsx> --hmin 1680 --hmax 1720 --age 20-69\n```\n")
md.append("```bash\npython export_and_render.py && python make_report.py\n```\n")
md.append("**직접 받아야 할 자료와 절차**\n\n"
          "1. https://sizekorea.kats.go.kr 회원가입·로그인\n"
          "2. 인체치수 데이터 → 제8차 직접측정 **원자료(개인별 raw data)** 신청. 통계표만 받으면 신장 168~172cm 집단을 "
          "추출할 수 없으므로 개인별 자료가 필요합니다.\n"
          "3. 같은 메뉴에서 2024 휠체어 사용자(척수손상) 측정 자료의 공개 여부와 항목표를 확인합니다. "
          "착석 자세 치수가 들어 있으면 일반 성인 값보다 이 값을 우선 적용합니다.\n"
          "4. 3D 표준인체형상(착석형이 있는지 확인)을 신청하고 받은 형상을 Rhino에서 Import합니다. "
          "서 있는 형상을 회전해 앉힌 것은 착석 스캔과 같다고 볼 수 없습니다.\n"
          "5. 받은 파일의 열 이름(키, 성별, 나이, 각 항목)이 스크립트 별칭과 다르면 `--map 항목=열이름`으로 지정합니다.\n")

# B
md.append("\n## B. 인체치수 → 제품치수 변환 계산표\n")
md.append(table(["그룹", "키", "값", "단위", "구분", "계산식/근거"],
                [[g, k, fmt(v), u, "[%s]" % t, f] for g, k, v, u, t, f in d.rows]))
md.append("\n인체 링크 모델 오프셋(모두 [임시 가정값]):\n\n")
md.append(table(["키", "값(mm)", "의미"], [[k, v[0], v[2]] for k, v in W.LINK.items()]))

# C
md.append("\n## C. 파트별 최종 치수표 (mm, 모델 바운딩박스 실측)\n")
with open(os.path.join(OUT, "parts_bbox.csv"), encoding="utf-8-sig") as f:
    r = list(csv.reader(f))
md.append(table(r[0], r[1:]))
md.append("\n주요 파트 파라미터(구분 포함)\n\n")
pr = [
    ["Seat Cushion", "유효 폭×깊이×두께", "%d × %d × %d" % (d.v["seat_width"], d.v["seat_depth"], W.R("cushion_thk")), "설계 산출 / 두께 임시"],
    ["Seat Cushion", "좌면 높이 전/후(압축)", "%d / %.0f" % (d.v["seat_front_h"], d.v["seat_rear_h"]), "설계 산출"],
    ["Backrest", "높이(좌면 기준)×폭, 각도", "%d × %d, 좌면-등받이 %d°" % (d.v["back_height"], d.v["back_width"], d.v["seat_back_angle"]), "설계 산출"],
    ["Headrest", "폭×높이×두께, 중심(등받이 방향)", "%d × %d × %d, %d" % (d.v["headrest_w"], d.v["headrest_h"], d.v["headrest_t"], d.v["headrest_center_s"]), "폭·중심 설계 산출 / 높이·두께 임시"],
    ["Armrests", "좌면 위 높이, 안쪽 간격, 길이×폭", "%d, %d, %d × %d" % (d.v["armrest_h_above_seat"], d.v["armrest_inner_gap"], d.v["armrest_len"], d.v["armrest_pad_w"]), "높이·간격 설계 산출 / 길이·폭 임시"],
    ["Rear Wheels", "직경×폭, 트레드", "%d × %d, %d" % (W.R("rear_D"), W.R("rear_W"), d.v["rear_track_cc"]), "임시(구조)"],
    ["Front Casters", "직경×폭, 트레드, 트레일", "%d × %d, %d, %d" % (W.R("caster_D"), W.R("caster_W"), d.v["front_track_cc"], W.R("caster_trail")), "임시(구조)"],
    ["Chassis", "전폭 / 전장(수납) / 휠베이스 / 지상고", "%d / %d / %d / %d" % (d.v["overall_width"], d.v["overall_length_stowed"], d.v["wheelbase"], W.R("ground_clear")), "설계 산출 + 임시"],
    ["Foot Platforms", "길이×폭×두께, 간격, 상면 높이", "%d × %d × %d, %d, %d" % (d.v["plate_len"], d.v["plate_w"], W.R("plate_thk"), d.v["plate_gap"], d.v["plate_top_h"]), "설계 산출 / 간격·두께 임시"],
]
md.append(table(["파트", "항목", "값", "구분"], pr))
md.append("\n파트별 치수는 `wc_model.py`의 `OVERRIDES` 딕셔너리로 다른 파트와 상관없이 바꿀 수 있습니다. "
          "예: `OVERRIDES[\"Headrest\"] = {\"w\": 300, \"center_s\": 780}`.\n")

# D/E
md.append("\n## D. Rhino 8 스크립트 / E. 3D 모델 파일\n")
md.append("| 파일 | 내용 |\n|---|---|\n"
          "| `wc_model.py` | **Rhino 8 ScriptEditor(Python 3)에서 바로 실행.** RhinoCommon으로 파트별 레이어 메시, 기준점 TextDot, 바운딩박스, MeshMeshFast 교차선(`_Interference` 레이어)을 만듭니다. 일반 Python에서는 계산 모듈로 쓰입니다. |\n"
          "| `export_and_render.py` | Rhino 없이 rhino3dm으로 `.3dm`을 내보내고 도면 PNG와 CSV를 생성합니다. |\n"
          "| `sizekorea_analysis.py` | 원자료에서 신장 168~172cm를 추출해 성별·연령대별 통계를 내고 모델 입력값(JSON)을 생성합니다. |\n"
          "| `out/RehabWheelchair_170cm_1to1.3dm` | 1:1 mm, 메시, 18개 레이어(13개 파트, 재활 자세 2개, 기준점, BBox) |\n")
md.append("\nRhino 사용: `ScriptEditor` → `wc_model.py` 열기 → Run. "
          "같은 폴더에 `anthropometry_sizekorea.json`이 있으면 자동으로 반영됩니다.\n\n"
          "**구현하지 않은 것:** NURBS/SubD 서피스, 실제 필렛 엣지, 힌지·슬라이드 메커니즘 구동, 구조 해석. "
          "형상은 라운드 박스·회전체 메시로 만든 기본 볼륨입니다. 정밀 형상은 이 볼륨을 기준으로 다시 모델링해야 합니다. "
          "Rhino 밖에서 실행하는 간섭 검사는 부품별 AABB 근사이며, 실제 형상 간섭은 Rhino의 MeshMeshFast 결과로 확인해야 합니다. "
          "이 컨테이너에는 Rhino가 없어 Rhino 실행부는 직접 실행해 보지 못했습니다.\n")

# F/G
md.append("\n## F. 정면도·측면도·평면도·사시도\n")
for n in ("views_front", "views_side", "views_top", "views_persp"):
    md.append("![%s](out/%s.png)\n" % (n, n))
md.append("\n## G. 170cm 더미 착석 검토\n")
md.append("더미는 위 인체치수(임시값)로 만든 **파라메트릭 캡슐·박스 더미**입니다. 사이즈코리아 3D 착석 스캔이 아닙니다.\n\n")
for n in ("views_persp_human", "seating_side_review", "seating_front_review", "seating_slide", "seating_pedal"):
    md.append("![%s](out/%s.png)\n" % (n, n))
md.append("\n### 착석 검토 결과\n")
v = d.v
gr = [
    ["엉덩이-좌석 접촉", "압축 좌면(쿠션 25mm 압축 가정)에 골반 하면이 닿도록 배치", "압축량 실측 필요"],
    ["허벅지 지지", "좌석깊이 %d = 엉덩이오금길이의 %.1f%%" % (v["seat_depth"], v["thigh_support_ratio"]), "OK(가정값 기준)"],
    ["무릎 뒤 여유", "P50 %d / P5 %d mm" % (v["knee_clear_P50"], v["knee_clear_P5"]), "OK(≥25)"],
    ["발판까지 거리", "좌석 전면 ↔ 발판 상면 %d mm, 정강이 전경 %.0f°, 무릎 내각 %.0f°" % (v["seat_front_h"] - v["plate_top_h"], v["shank_incline_deg"], v["knee_angle_seated"]), "발판 높이 조절 ±30 권장"],
    ["팔꿈치-팔걸이", "팔걸이 = 앉은팔꿈치높이 + %d" % W.R("elbow_rest_offset"), "OK(가정값 기준)"],
    ["등-등받이", "등받이 높이 %d(어깨 −30), 요추 %d, 견갑 %d" % (v["back_height"], v["lumbar_center"], v["shoulder_support"]), "요추 위치 문헌·실측 확인"],
    ["후두부-헤드레스트", "중심 %d (등받이 방향), 전방 오프셋 %d" % (v["headrest_center_s"], v["headrest_fwd_offset"]), "상하 ±50·전후 ±40 조절식 권장"],
]
md.append(table(["항목", "결과", "판정/메모"], gr))
md.append("\n### 간섭·여유 검사 (`out/checks.csv`)\n")
with open(os.path.join(OUT, "checks.csv"), encoding="utf-8-sig") as f:
    r = list(csv.reader(f))
md.append(table(r[0], [x for x in r[1:] if x[0] != "BBox"]))
md.append("\nBBox 겹침 목록(조립 접합부를 포함하는 거친 검사)은 `out/checks.csv`에 있습니다.\n")

md.append("\n### 재활 발판 — 두 방식 비교\n")
s, pe = v.get("slide"), v.get("pedal")
md.append(table(["구분", "전후 슬라이딩식", "회전 페달식"], [
    ["운동", "발판이 경사 레일을 따라 전진·상승(레그프레스형)", "크랭크 원운동(사이클형)"],
    ["산출 배치", "레일 %s°, 스트로크 %s mm" % (s["angle"], s["stroke"]) if s else "해 없음",
     "크랭크 중심 x=%s, h=%s, r=%s" % (pe["cx"], pe["cz"], pe["r"]) if pe else "해 없음"],
    ["무릎 내각 범위", "%.0f° → %.0f°" % (v["knee_angle_seated"], s["knee"]) if s else "-",
     "%.0f° ~ %.0f°" % (pe["kmin"], pe["kmax"]) if pe else "-"],
    ["전방 점유", "신전 끝 발판 전단 x=%s" % v.get("plate_front_x_at_end"), "페달 궤적 전단 x=%s" % (pe["cx"] + pe["r"] + 150 if pe else "-")],
    ["구조", "중앙 스파인 + 경사 레일 + 캐리지(직선 액추에이터)", "중앙 스파인 + 크랭크 하우징(모터/저항), 좌우 페달 위상차 180°"],
    ["발 이탈 방지", "뒤꿈치 지지대 + 외측 가드 + 발등 스트랩", "페달 스트랩/힐컵 필수, 회전 중 발 미끄럼 위험"],
    ["수납", "레일 후퇴 시 일반 발판으로 사용", "페달을 발판 위치로 고정하거나 교체 모듈"],
]))
md.append("\n공통 차체(중앙 스파인, 전면 라이저, 캐리지 바)를 먼저 모델링했고, 두 방식은 `Rehab Pose - *` 레이어에 참조 형상으로만 넣었습니다. "
          "탐색 조건(무릎 내각 75~150°, 허벅지가 좌면 아래로 내려가지 않음, 페달 최저 지상고 50mm, 캐스터 궤적 회피)은 "
          "모두 **[임시 가정값]**입니다. 재활 효과와 안전성을 보장하지 않습니다.\n")

# H
md.append("\n## H. 인체공학 검증이 필요한 부분과 설계 한계\n")
md.append("""1. **인체치수 전부가 임시값입니다.** 사이즈코리아 원자료로 교체하기 전에는 이 모델로 치수를 확정하면 안 됩니다.
2. 170cm만 기준으로 하면 남녀 체형 차이(엉덩이 너비, 앉은키 비율)가 큽니다. 원자료로 남녀를 나눠 보고, 폭 치수는 큰 쪽의 P95, 길이 치수는 작은 쪽의 P5로 검토하세요.
3. 휠체어 사용자(척수손상)는 근위축·자세 변형·욕창 위험 때문에 일반 성인과 치수 분포가 다를 수 있습니다. 2024 휠체어 사용자 자료를 우선 적용해야 합니다.
4. 관절 중심 오프셋(LINK), 쿠션 압축량, 요추 지지 위치, 후두부 오프셋은 문헌 확인과 실측이 필요합니다.
5. 바퀴 직경, 트레일, 휠베이스, 질량, CG는 구조·안정성 가정입니다. ISO 7176-1(정적 안정성), ISO 7176-2(동적 안정성), ISO 7176-5(치수·회전 공간) 시험이나 해석으로 확인해야 합니다. 제자리 회전 직경 %d mm는 개략 계산값입니다.
6. 슬라이딩식은 무릎을 150°까지 펴려면 레일을 %s° 정도로 경사지게 해야 합니다. 의자 기울기·등받이 리클라인과 연동할지 검토가 필요합니다. 신전 시 전장이 늘어나므로 실내 회전 공간도 다시 확인해야 합니다.
7. 회전 페달식은 캐스터를 피하고 무릎·고관절 각도 조건을 만족하는 크랭크 위치를 찾았지만, 발 고정·근긴장(경직)·관절 가동범위는 임상 검증 대상입니다.
8. 팔걸이로 측면 이승을 하려면 스윙업 또는 탈착 구조가 필요합니다(현재는 형상만 있고 힌지는 없음).
9. 캐스터를 90° 돌리면 폭이 %d mm까지 늘어납니다(정지 시 전폭 %d mm).
10. 메시 기반 기본 볼륨이라 표면 품질, 엣지 연결, CMF는 컨셉 수준입니다.
""" % (v["pivot_turn_diameter"], s["angle"] if s else "-", v["overall_width_caster_swept"], v["overall_width"]))

with open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("REPORT.md written")
