#! python3
# -*- coding: utf-8 -*-
"""
재활휠체어 1:1 기본 볼륨 모델 (Size Korea 기반 170cm 성인 기준) — 파라메트릭 모델

실행 환경
  * Rhino 8 ScriptEditor (CPython 3)  : RhinoCommon 으로 현재 문서에 레이어별 메시를 생성하고
                                        MeshMeshFast 간섭 검사 + 기준점 TextDot 을 추가합니다.
  * 일반 Python 3 + rhino3dm          : `python export_and_render.py` 가 이 모듈을 import 하여
                                        .3dm 파일과 도면 이미지를 만듭니다.

좌표계 (단위 mm)
  원점 = 바닥면, 차체 중심선, 후륜 차축 바로 아래
  +X = 전방, +Y = 사용자 왼쪽, +Z = 위

값 태그
  [공식 측정값]  사이즈코리아 원자료에서 확인한 값  (현재 파일에는 없음 — 원자료 접근 불가)
  [설계 산출값]  측정값/가정값에서 명시적 계산으로 도출한 값
  [임시 가정값]  검증되지 않은 모델링용 값

주의: 이 모델은 메시 기반 '기본 볼륨' 모델입니다. NURBS 서피스/필렛 형상, 실제 구조 해석,
      재활 효과·안전성 검증은 포함되어 있지 않습니다.
"""
import math
import json
import os

OFFICIAL = "공식 측정값"
DERIVED = "설계 산출값"
ASSUMED = "임시 가정값"

# =============================================================================
# 1. 인체치수 입력 (사이즈코리아 원자료로 교체해야 하는 값)
#    현재 값은 모두 [임시 가정값] 입니다. 사이즈코리아 공식 수치가 아닙니다.
#    sizekorea_analysis.py 가 생성한 anthropometry_sizekorea.json 이 같은 폴더에 있으면
#    해당 값으로 자동 교체되고 태그가 [공식 측정값] 으로 바뀝니다.
# =============================================================================
ANTHRO = {
    # key: (value_mm, tag, note)
    "키":                      (1700, ASSUMED, "설계 기준 신장(요구조건)"),
    "앉은키":                  (905, ASSUMED, "P50 자리표시값"),
    "앉은눈높이":              (790, ASSUMED, "P50 자리표시값"),
    "앉은어깨높이":            (590, ASSUMED, "P50 자리표시값"),
    "앉은팔꿈치높이":          (250, ASSUMED, "P50 자리표시값"),
    "앉은넙다리높이":          (150, ASSUMED, "P50 자리표시값"),
    "앉은무릎높이":            (520, ASSUMED, "P50 자리표시값"),
    "앉은오금높이":            (410, ASSUMED, "P50 자리표시값"),
    "앉은오금높이_P5":         (390, ASSUMED, "P5 자리표시값"),
    "앉은엉덩이너비":          (370, ASSUMED, "P50 자리표시값"),
    "앉은엉덩이너비_P95":      (400, ASSUMED, "P95 자리표시값(좌석 폭 수용)"),
    "앉은엉덩이오금수평길이":  (470, ASSUMED, "P50 자리표시값"),
    "앉은엉덩이오금수평길이_P5": (445, ASSUMED, "P5 자리표시값(무릎 뒤 여유 검토)"),
    "앉은엉덩이무릎수평길이":  (570, ASSUMED, "P50 자리표시값"),
    "어깨너비":                (380, ASSUMED, "P50 자리표시값"),
    "어깨최대너비":            (450, ASSUMED, "명칭·수록 여부 확인 필요"),
    "앉은팔꿈치사이너비":      (470, ASSUMED, "명칭·수록 여부 확인 필요"),
    "팔꿈치손목길이":          (260, ASSUMED, "명칭·수록 여부 확인 필요"),
    "발길이":                  (250, ASSUMED, "P50 자리표시값"),
    "발너비":                  (100, ASSUMED, "P50 자리표시값"),
    "머리너비":                (160, ASSUMED, "P50 자리표시값"),
    "머리길이":                (190, ASSUMED, "P50 자리표시값"),
    "머리수직길이":            (230, ASSUMED, "P50 자리표시값"),
}

# 인체 링크(관절 중심) 모델 오프셋 — 모두 문헌 확인 전 [임시 가정값]
LINK = {
    "hip_fwd_from_buttock":   (130, ASSUMED, "엉덩이 후면 → 고관절 중심 수평거리"),
    "hip_above_seat":         (85,  ASSUMED, "압축 좌면 → 고관절 중심 높이"),
    "knee_pivot_behind_front": (55, ASSUMED, "무릎 앞면 → 무릎관절 중심"),
    "knee_pivot_above_popliteal": (45, ASSUMED, "오금 하면 → 무릎관절 중심"),
    "ankle_above_sole":       (80,  ASSUMED, "신발 밑창 → 발목관절 중심(신발 포함)"),
    "ankle_fwd_of_heel":      (60,  ASSUMED, "뒤꿈치 후면 → 발목관절 중심"),
    "shoe_allowance":         (25,  ASSUMED, "신발 밑창 두께"),
    "occiput_below_vertex":   (110, ASSUMED, "정수리 → 후두부 최돌출점 수직거리"),
    "occiput_fwd_of_back":    (50,  ASSUMED, "등받이면 → 후두부 전방 오프셋(흉추 후만)"),
    "torso_depth":            (220, ASSUMED, "앉은 몸통 두께"),
}

# =============================================================================
# 2. 설계 규칙/구조 파라미터 (인체치수와 무관한 값은 별도 표기)
# =============================================================================
RULE = {
    # --- 좌석 ---
    "seat_side_clear":     (25, ASSUMED, "좌석 폭 좌우 여유(한쪽)"),
    "knee_clear":          (60, ASSUMED, "오금 여유(엉덩이오금길이 - 좌석깊이)"),
    "cushion_thk":         (80, ASSUMED, "좌석 쿠션 두께(비압축)"),
    "cushion_compress":    (25, ASSUMED, "착석 시 좌골부 압축량 — 폼 밀도별 실측 필요"),
    "front_round_r":       (30, ASSUMED, "좌석 전면 라운드 반경(워터폴)"),
    "seat_tilt_deg":       (4,  ASSUMED, "좌면 전방 상향 경사"),
    "back_recline_deg":    (12, ASSUMED, "등받이 수직 대비 후경각"),
    "footplate_min_top":   (80, ASSUMED, "발판 상면 최저 높이 = 지상고50+판두께20+여유10"),
    "shank_rise":          (15, ASSUMED, "정강이 15° 전경을 위한 발판 상향량"),
    # --- 등받이/헤드레스트 ---
    "back_top_below_shoulder": (30, ASSUMED, "등받이 상단 = 앉은어깨높이 - 30"),
    "back_cushion_thk":    (70, ASSUMED, ""),
    "back_shell_thk":      (35, ASSUMED, ""),
    "lumbar_center":       (200, ASSUMED, "요추 지지 중심(좌면 기준, 등받이 방향) — 문헌 확인 필요"),
    "shoulder_support_ratio": (0.85, ASSUMED, "견갑부 지지 = 앉은어깨높이 x 0.85"),
    "head_side_margin":    (60, ASSUMED, "헤드레스트 폭 = 머리너비 + 2x60"),
    "headrest_h":          (160, ASSUMED, ""),
    "headrest_t":          (70, ASSUMED, ""),
    # --- 팔걸이/조이스틱 ---
    "elbow_rest_offset":   (20, ASSUMED, "팔걸이 = 앉은팔꿈치높이 + 20"),
    "arm_inner_extra":     (15, ASSUMED, "팔걸이 안쪽 간격 = 좌석폭 + 2x15"),
    "arm_len":             (330, ASSUMED, ""),
    "arm_pad_w":           (70, ASSUMED, ""),
    "arm_pad_h":           (40, ASSUMED, ""),
    "arm_struct_w":        (80, ASSUMED, ""),
    "joystick_grip":       (60, ASSUMED, "손바닥 중심까지 추가 길이"),
    # --- 바퀴/차체 (인체치수와 무관한 구조·안정성 가정) ---
    "rear_D":              (320, ASSUMED, "후륜 직경(구동)"),
    "rear_W":              (75,  ASSUMED, "후륜 폭"),
    "caster_D":            (200, ASSUMED, "전륜(캐스터) 직경"),
    "caster_W":            (50,  ASSUMED, ""),
    "caster_trail":        (45,  ASSUMED, "스위블축 → 캐스터 차축 트레일"),
    "caster_clear":        (25,  ASSUMED, "캐스터 회전 궤적 ↔ 발판 최소 간격"),
    "wheelbase_target":    (470, ASSUMED, "목표 휠베이스(전방 안정성)"),
    "ground_clear":        (70,  ASSUMED, "차체 최저 지상고"),
    "wheel_body_clear":    (15,  ASSUMED, "바퀴 ↔ 차체 간격"),
    "max_width":           (700, ASSUMED, "실내 통행 목표 전폭 상한"),
    "caster_out_allow":    (40, ASSUMED, "캐스터 측방 회전 시 팔걸이 외곽 대비 허용 돌출"),
    "spine_w":             (90, ASSUMED, "재활 장치 중앙 스파인 폭"),
    # --- 발판/재활 ---
    "plate_len_extra":     (30, ASSUMED, "발판 길이 = 발길이 + 30"),
    "plate_w_extra":       (40, ASSUMED, "발판 폭 = 발너비 + 40"),
    "plate_gap":           (40, ASSUMED, "좌우 발판 사이 간격"),
    "plate_thk":           (20, ASSUMED, ""),
    "heel_loop_h":         (60, ASSUMED, "뒤꿈치 지지대 높이"),
    "side_guard_h":        (40, ASSUMED, "외측 가드 높이"),
    "knee_max_deg":        (150, ASSUMED, "재활 모드 최대 무릎 내각(신전 한계) — 임상 검증 필요"),
    "knee_min_deg":        (75,  ASSUMED, "회전 페달 최소 무릎 내각 — 임상 검증 필요"),
    "hip_flex_thigh_max":  (40,  ASSUMED, "허벅지 최대 상승각(수평 기준)"),
    "crank_r":             (90,  ASSUMED, "회전 페달 크랭크 반경"),
    "user_mass":           (70,  ASSUMED, "안정성 개략검토용 사용자 질량 kg"),
    "chair_mass":          (120, ASSUMED, "안정성 개략검토용 차체 질량 kg"),
}

# 파트별 독립 치수 변경: 예) OVERRIDES["Headrest"] = {"w": 300}
OVERRIDES = {
    "Seat Cushion": {}, "Backrest": {}, "Headrest": {}, "Left Armrest": {}, "Right Armrest": {},
    "Side Body": {}, "Lower Chassis": {}, "Rear Wheels": {}, "Front Casters": {},
    "Rehabilitation Mechanism": {}, "Left Foot Platform": {}, "Right Foot Platform": {},
    "Human Reference": {},
}

PART_ORDER = ["Seat Cushion", "Backrest", "Headrest", "Left Armrest", "Right Armrest",
              "Side Body", "Lower Chassis", "Rear Wheels", "Front Casters",
              "Rehabilitation Mechanism", "Left Foot Platform", "Right Foot Platform",
              "Human Reference"]

COLORS = {
    "white": (236, 236, 233), "fabric": (178, 180, 183), "graphite": (72, 74, 79),
    "silver": (192, 194, 198), "tire": (48, 48, 52), "accent": (96, 200, 150),
    "human": (214, 168, 140), "ghost": (120, 160, 225), "ghost2": (235, 150, 90),
}


def load_sizekorea_override(folder):
    """sizekorea_analysis.py 결과(JSON)를 읽어 ANTHRO 를 [공식 측정값]으로 교체."""
    p = os.path.join(folder, "anthropometry_sizekorea.json")
    if not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    for k, rec in data.get("values", {}).items():
        if k in ANTHRO and rec.get("value") is not None:
            ANTHRO[k] = (float(rec["value"]), OFFICIAL, rec.get("note", ""))
    return True


# =============================================================================
# 3. 치수 산정 (인체치수 → 제품치수)
# =============================================================================
class Dims(object):
    def __init__(self):
        self.rows = []      # (group, name, value, unit, tag, formula)
        self.v = {}

    def set(self, group, key, value, tag, formula, unit="mm"):
        self.v[key] = value
        self.rows.append((group, key, value, unit, tag, formula))
        return value


def A(k):
    return ANTHRO[k][0]


def R(k):
    return RULE[k][0]


def Lk(k):
    return LINK[k][0]


def rot2(vx, vz, deg):
    a = math.radians(deg)
    return (vx * math.cos(a) - vz * math.sin(a), vx * math.sin(a) + vz * math.cos(a))


def ik_2link(H, T, L1, L2):
    """고관절 H(x,z) 고정, 발목 목표 T. 무릎 상향해. 반환 (knee, knee_inner_deg, thigh_deg) 또는 None"""
    dx, dz = T[0] - H[0], T[1] - H[1]
    d = math.hypot(dx, dz)
    if d > L1 + L2 - 1e-6 or d < abs(L1 - L2) + 1e-6:
        return None
    a = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    base = math.atan2(dz, dx)
    K = (H[0] + L1 * math.cos(base + a), H[1] + L1 * math.sin(base + a))
    knee = math.degrees(math.acos(max(-1, min(1, (L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2)))))
    thigh = math.degrees(math.atan2(K[1] - H[1], K[0] - H[0]))
    return K, knee, thigh


def derive():
    d = Dims()
    S = "좌석"
    # ---- 좌석 ----
    sw = d.set(S, "seat_width", A("앉은엉덩이너비_P95") + 2 * R("seat_side_clear"), DERIVED,
               "앉은엉덩이너비(P95) + 2×좌우여유")
    sd = d.set(S, "seat_depth", A("앉은엉덩이오금수평길이") - R("knee_clear"), DERIVED,
               "앉은엉덩이오금수평길이 − 오금여유")
    d.set(S, "knee_clear_P50", A("앉은엉덩이오금수평길이") - sd, DERIVED, "P50 오금 여유")
    d.set(S, "knee_clear_P5", A("앉은엉덩이오금수평길이_P5") - sd, DERIVED, "P5 오금 여유(≥25 권장)")
    d.set(S, "thigh_support_ratio", round(sd / A("앉은엉덩이오금수평길이") * 100, 1), DERIVED,
          "좌석깊이 / 엉덩이오금길이", unit="%")
    sf = d.set(S, "seat_front_h", R("footplate_min_top") + A("앉은오금높이") + Lk("shoe_allowance"), DERIVED,
               "발판최저상면 + 앉은오금높이 + 신발")
    d.set(S, "cushion_thk", R("cushion_thk"), ASSUMED, "")
    d.set(S, "cushion_compress", R("cushion_compress"), ASSUMED, "실측 필요")
    d.set(S, "front_round_r", R("front_round_r"), ASSUMED, "")
    tilt = R("seat_tilt_deg")
    sr = d.set(S, "seat_rear_h", round(sf - sd * math.sin(math.radians(tilt)), 1), DERIVED,
               "좌석전면높이 − 깊이×sin(경사)")
    d.set(S, "seat_rear_h_uncompressed", sr + R("cushion_compress"), DERIVED, "비착석 시 좌면 후부 높이")

    # ---- 인체 링크 (좌석 후단 x = sx 미정 → 상대좌표로 먼저 계산) ----
    hip_rel = (Lk("hip_fwd_from_buttock"), sr + Lk("hip_above_seat"))
    knee_rel = (A("앉은엉덩이무릎수평길이") - Lk("knee_pivot_behind_front"),
                sf + Lk("knee_pivot_above_popliteal"))
    L1 = math.hypot(knee_rel[0] - hip_rel[0], knee_rel[1] - hip_rel[1])
    L2 = A("앉은오금높이") + Lk("knee_pivot_above_popliteal") + Lk("shoe_allowance") - Lk("ankle_above_sole")
    H = "인체링크"
    d.set(H, "L1_thigh", round(L1, 1), DERIVED, "고관절→무릎관절 (엉덩이무릎길이·오프셋 기반)")
    d.set(H, "L2_shank", L2, DERIVED, "무릎관절→발목 = 오금높이 + 45 + 신발 − 80")
    plate_top = d.set("발판", "plate_top_h", sf - A("앉은오금높이") - Lk("shoe_allowance") + R("shank_rise"),
                      DERIVED, "좌석전면높이 − 오금높이 − 신발 + 상향량")
    ankle_z = plate_top + Lk("ankle_above_sole")
    c = (knee_rel[1] - ankle_z) / L2
    shank_deg = math.degrees(math.acos(max(-1, min(1, c))))
    d.set(H, "shank_incline_deg", round(shank_deg, 1), DERIVED, "착석 기본자세 정강이 전경각", unit="°")
    ankle_rel = (knee_rel[0] + L2 * math.sin(math.radians(shank_deg)), ankle_z)
    heel_rel = ankle_rel[0] - Lk("ankle_fwd_of_heel")

    # ---- 바퀴/차체: 캐스터 회전 궤적이 발판 뒤에 오도록 좌석 위치를 결정 ----
    cR = R("caster_D") / 2.0
    env = math.hypot(R("caster_trail") + cR, R("caster_W") / 2.0)
    W = "바퀴·차체(구조 가정 기반)"
    d.set(W, "caster_swivel_envelope_r", round(env, 1), DERIVED, "√((트레일+R)²+(W/2)²)")
    wb = R("wheelbase_target")
    xs = wb + R("caster_trail")                       # 스위블축 x
    heel_x = xs + env + R("caster_clear")
    sx = heel_x - heel_rel                            # 좌석 후단(등받이 전면) x
    d.set(W, "wheelbase", wb, ASSUMED, "목표 휠베이스(후륜축↔캐스터축)")
    d.set(W, "caster_swivel_x", xs, DERIVED, "휠베이스 + 트레일")
    d.set(S, "seat_rear_x", round(sx, 1), DERIVED, "발판 뒤꿈치 = 스위블x + 궤적반경 + 간격 에서 역산")
    d.set(S, "seat_front_x", round(sx + sd * math.cos(math.radians(tilt)), 1), DERIVED, "")
    hip = (sx + hip_rel[0], hip_rel[1])
    knee = (sx + knee_rel[0], knee_rel[1])
    ankle = (sx + ankle_rel[0], ankle_rel[1])
    d.v["hip"], d.v["knee"], d.v["ankle"] = hip, knee, ankle
    d.v["L1"], d.v["L2"] = L1, L2
    knee0 = ik_2link(hip, ankle, L1, L2)
    d.set(H, "knee_angle_seated", round(knee0[1], 1), DERIVED, "착석 기본자세 무릎 내각", unit="°")
    d.v["_thigh0"] = knee0[2]
    d.set(H, "thigh_angle_seated", round(knee0[2], 1), DERIVED, "착석 허벅지 각(수평 기준, +상향)", unit="°")

    # ---- 등받이/헤드레스트 ----
    B = "등받이·헤드레스트"
    rec = R("back_recline_deg")
    d.set(B, "seat_back_angle", 90 + rec - tilt, DERIVED, "90 + 후경각 − 좌면경사", unit="°")
    bh = d.set(B, "back_height", A("앉은어깨높이") - R("back_top_below_shoulder"), DERIVED,
               "앉은어깨높이 − 30 (등받이 방향 거리)")
    d.set(B, "back_width", sw, DERIVED, "= 좌석 폭 (어깨너비 P50 보다 넓음 확인)")
    d.set(B, "back_width_vs_shoulder", sw - A("어깨너비"), DERIVED, "등받이폭 − 어깨너비")
    d.set(B, "lumbar_center", R("lumbar_center"), ASSUMED, "문헌(요추 L3–L4) 확인 필요")
    d.set(B, "shoulder_support", round(A("앉은어깨높이") * R("shoulder_support_ratio")), DERIVED,
          "앉은어깨높이 × 0.85")
    hs = d.set(B, "headrest_center_s", A("앉은키") - Lk("occiput_below_vertex"), DERIVED,
               "앉은키 − 정수리~후두부 (등받이 방향)")
    d.set(B, "headrest_w", A("머리너비") + 2 * R("head_side_margin"), DERIVED, "머리너비 + 2×60")
    d.set(B, "headrest_h", R("headrest_h"), ASSUMED, "")
    d.set(B, "headrest_t", R("headrest_t"), ASSUMED, "")
    d.set(B, "headrest_fwd_offset", Lk("occiput_fwd_of_back"), ASSUMED, "등받이면 대비 전방(조절식 필요)")
    d.set(B, "headrest_gap_back", hs - R("headrest_h") / 2 - bh, DERIVED, "등받이 상단~헤드레스트 하단")

    # ---- 팔걸이 ----
    Ar = "팔걸이·조이스틱"
    ah = d.set(Ar, "armrest_h_above_seat", A("앉은팔꿈치높이") + R("elbow_rest_offset"), DERIVED,
               "앉은팔꿈치높이 + 20 (압축 좌면 기준)")
    d.set(Ar, "armrest_top_abs", round(sr + ah, 1), DERIVED, "바닥 기준")
    ai = d.set(Ar, "armrest_inner_gap", sw + 2 * R("arm_inner_extra"), DERIVED, "좌석폭 + 2×15")
    d.set(Ar, "armrest_len", R("arm_len"), ASSUMED, "")
    d.set(Ar, "armrest_pad_w", R("arm_pad_w"), ASSUMED, "")
    d.set(Ar, "elbow_zone", "등받이면 +40 ~ +200", ASSUMED, "팔꿈치 지지 구간", unit="")
    jx = d.set(Ar, "joystick_from_back", A("팔꿈치손목길이") + R("joystick_grip") + 60, DERIVED,
               "팔꿈치(등받이+60) + 팔꿈치손목길이 + 그립")
    d.set(Ar, "transfer_opening", round(sd), DERIVED, "팔걸이 스윙업 시 측면 이승 개구 길이 ≈ 좌석깊이")

    # ---- 바퀴/차체 계속 ----
    rW, rR = R("rear_W"), R("rear_D") / 2.0
    arm_outer = ai / 2 + R("arm_struct_w")
    y_rw = arm_outer - rW / 2
    d.set(W, "rear_track_cc", round(2 * y_rw), DERIVED, "팔걸이 외곽에 후륜 외곽을 맞춤")
    d.set(W, "rear_wheel_D_W", "%d × %d" % (R("rear_D"), rW), ASSUMED, "", unit="mm")
    d.set(W, "caster_D_W", "%d × %d" % (R("caster_D"), R("caster_W")), ASSUMED, "", unit="mm")
    d.v["y_rw"] = y_rw
    d.v["arm_outer"] = arm_outer
    # 캐스터 y: 회전궤적 외곽 ≤ 팔걸이 외곽 + 허용돌출, 궤적 안쪽 ≥ 스파인/2 + 15
    y_c = arm_outer + R("caster_out_allow") - env
    d.v["y_c"] = y_c
    d.set(W, "front_track_cc", round(2 * y_c), DERIVED, "2×(팔걸이외곽 + 허용돌출 − 회전궤적반경)")
    d.set(W, "caster_env_vs_spine", round(y_c - env - R("spine_w") / 2.0, 1), DERIVED,
          "캐스터 궤적 안쪽 ↔ 중앙 스파인 간격(≥15)")
    width = 2 * max(arm_outer, y_rw + rW / 2, y_c + R("caster_W") / 2.0)
    d.set(W, "overall_width", round(width), DERIVED, "max(팔걸이, 후륜, 캐스터 후향 정지) ×2")
    d.set(W, "overall_width_caster_swept", round(2 * (y_c + env)), DERIVED, "캐스터 90° 회전 시 최대 폭")
    d.set(W, "ground_clear", R("ground_clear"), ASSUMED, "")

    # ---- 발판 ----
    F = "발판"
    pl = d.set(F, "plate_len", A("발길이") + R("plate_len_extra"), DERIVED, "발길이 + 30")
    pw = d.set(F, "plate_w", A("발너비") + R("plate_w_extra"), DERIVED, "발너비 + 40")
    pg = d.set(F, "plate_gap", R("plate_gap"), ASSUMED, "")
    d.set(F, "plate_center_y", pg / 2 + pw / 2, DERIVED, "")
    d.set(F, "plate_heel_x", round(heel_x, 1), DERIVED, "")
    d.set(F, "plate_bottom_h", plate_top - R("plate_thk"), DERIVED, "발판 최저 지상고(기본자세)")
    rear_back = -rR
    front = heel_x + pl
    d.set(W, "overall_length_stowed", round(front - min(rear_back, sx - 160)), DERIVED,
          "후륜 후단(또는 등받이 후면) ~ 발판 전단")
    d.set(F, "plate_y_outer", pg / 2 + pw, DERIVED, "")
    d.set(F, "caster_env_inner_y", round(y_c - env, 1), DERIVED, "")

    # ---- 재활: 슬라이딩식 ----
    rail = slide_analysis(d, hip, ankle, L1, L2, plate_top)
    pedal = pedal_analysis(d, hip, L1, L2, xs, env)
    d.v["slide"], d.v["pedal"] = rail, pedal

    # ---- 회전반경(제자리 회전, 후륜축 중점 기준) ----
    corners = [(front, pg / 2 + pw), (-rR, y_rw + rW / 2), (sx - 160, sw / 2), (xs + env, y_c + env)]
    rmax = max(math.hypot(x, y) for x, y in corners)
    d.set(W, "pivot_turn_diameter", round(2 * rmax), DERIVED,
          "후륜 차동 제자리회전 시 최외곽점 궤적 직경(개략, ISO 7176-5 시험 대체 불가)")

    # ---- 정적 안정성 개략 ----
    um, cm = R("user_mass"), R("chair_mass")
    ucg = hip[0] + 60
    ccg = (xs * 0.35)
    cg = (um * ucg + cm * ccg) / (um + cm)
    d.set(W, "cg_x_est", round(cg), ASSUMED, "사용자CG(고관절+60)·차체CG(휠베이스 35%) 가중평균 — 실측 필요")
    d.set(W, "rear_tip_margin", round(cg), DERIVED, "CG ~ 후륜 접지점 수평거리(정적)")
    d.set(W, "front_tip_margin", round(wb - cg), DERIVED, "CG ~ 캐스터 접지점 수평거리(정적)")
    return d


def slide_analysis(d, hip, ankle0, L1, L2, plate_top):
    """전후 슬라이딩 발판: 레일 각도별 무릎 내각이 knee_max 에 도달하는 스트로크 탐색.
    조건: 허벅지 각 ≥ 착석각(좌면 아래로 내려가지 않음) & ≤ hip_flex_thigh_max."""
    thigh0 = ik_2link(hip, ankle0, L1, L2)[2]
    best = None
    rows = []
    for ang in range(0, 61, 5):
        ux, uz = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        ok_stroke, end = None, None
        for s in range(0, 601, 5):
            T = (ankle0[0] + ux * s, ankle0[1] + uz * s)
            r = ik_2link(hip, T, L1, L2)
            if r is None:
                break
            K, kn, th = r
            if th < thigh0 - 2 or th > R("hip_flex_thigh_max"):
                break
            ok_stroke, end = s, (T, K, kn, th)
            if kn >= R("knee_max_deg"):
                break
        reached = end is not None and end[2] >= R("knee_max_deg") - 0.5
        rows.append((ang, ok_stroke, round(end[2], 1) if end else None, round(end[3], 1) if end else None, reached))
        if reached and (best is None or ok_stroke < best[1]):
            best = (ang, ok_stroke, end)
    G = "재활-슬라이딩식"
    d.v["slide_table"] = rows
    if best:
        ang, s, (T, K, kn, th) = best
        d.set(G, "rail_angle", ang, DERIVED, "도달 가능한 최소 스트로크 레일각(수평 기준)", unit="°")
        d.set(G, "stroke", s, DERIVED, "기본자세 → 무릎 내각 %d° 까지" % R("knee_max_deg"))
        d.set(G, "knee_range", "%.0f° → %.0f°" % (ik_2link(hip, ankle0, L1, L2)[1], kn), DERIVED, "", unit="")
        d.set(G, "plate_top_at_end", round(T[1] - Lk("ankle_above_sole")), DERIVED, "신전 끝 발판 상면 높이")
        d.set(G, "plate_front_x_at_end",
              round(T[0] - Lk("ankle_fwd_of_heel") + A("발길이") + R("plate_len_extra")), DERIVED, "신전 끝 발판 전단 x")
        return {"angle": ang, "stroke": s, "end_ankle": T, "end_knee": K, "knee": kn, "thigh": th}
    d.set(G, "rail_angle", "해 없음", DERIVED, "조건 내 도달 불가 — 등받이 리클라인 필요", unit="")
    return None


def pedal_analysis(d, hip, L1, L2, xs, env):
    """회전 페달: 크랭크 중심 그리드 탐색 → 조건 만족 & 전방 돌출 최소."""
    cr = R("crank_r")
    best = None
    for cx10 in range(int(hip[0] + 300) // 10, int(hip[0] + 900) // 10):
        cx = cx10 * 10
        for cz in range(100, 600, 10):
            ok, kmin, kmax, tmin = True, 999, 0, 999
            for i in range(24):
                ph = 2 * math.pi * i / 24
                px, pz = cx + cr * math.cos(ph), cz + cr * math.sin(ph)
                if pz - 20 < 50:                      # 페달 하단 지상고 50
                    ok = False; break
                if pz < R("caster_D") + 20 and abs(px - xs) < env + R("caster_clear"):
                    ok = False; break
                T = (px - 30 + Lk("ankle_fwd_of_heel") - 60, pz + Lk("ankle_above_sole") - 10)
                r = ik_2link(hip, T, L1, L2)
                if r is None:
                    ok = False; break
                K, kn, th = r
                if kn < R("knee_min_deg") or kn > R("knee_max_deg") or th < d.v["_thigh0"] - 2 \
                        or th > R("hip_flex_thigh_max"):
                    ok = False; break
                kmin, kmax, tmin = min(kmin, kn), max(kmax, kn), min(tmin, th)
            if ok:
                key = (cx, -cz)
                if best is None or key < best[0]:
                    best = (key, cx, cz, kmin, kmax, tmin)
        if best:
            break
    G = "재활-회전페달식"
    if best:
        _, cx, cz, kmin, kmax, tmin = best
        d.set(G, "crank_r", cr, ASSUMED, "")
        d.set(G, "crank_center_x", cx, DERIVED, "조건 만족 최소 전방 위치(그리드 10mm)")
        d.set(G, "crank_center_h", cz, DERIVED, "")
        d.set(G, "knee_range", "%.0f° ~ %.0f°" % (kmin, kmax), DERIVED, "1회전 중 무릎 내각", unit="")
        d.set(G, "pedal_low_h", cz - cr - 20, DERIVED, "페달 최저점 지상고")
        return {"cx": cx, "cz": cz, "r": cr, "kmin": kmin, "kmax": kmax}
    d.set(G, "crank_center_x", "해 없음", DERIVED, "조건 내 해 없음", unit="")
    return None


# =============================================================================
# 4. 메시 기하 (순수 파이썬 — Rhino/rhino3dm 공통)
# =============================================================================
class Mesh(object):
    def __init__(self):
        self.v, self.f = [], []

    def extend(self, o):
        n = len(self.v)
        self.v += o.v
        self.f += [tuple(i + n for i in face) for face in o.f]
        return self

    def map(self, fn):
        self.v = [fn(p) for p in self.v]
        return self

    def move(self, dx, dy, dz):
        return self.map(lambda p: (p[0] + dx, p[1] + dy, p[2] + dz))

    def rot_y(self, deg, cx=0, cz=0):
        # 측면(XZ)에서 +deg 는 X→Z (앞쪽이 들림)
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        return self.map(lambda p: (cx + (p[0] - cx) * c - (p[2] - cz) * s, p[1],
                                   cz + (p[0] - cx) * s + (p[2] - cz) * c))

    def bbox(self):
        xs = [p[0] for p in self.v]; ys = [p[1] for p in self.v]; zs = [p[2] for p in self.v]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _samples(h, r, k, m):
    out = []
    for i in range(k):
        out.append(-h + r * i / float(k))
    inner = h - r
    for i in range(m + 1):
        out.append(-inner + 2 * inner * i / float(m))
    for i in range(1, k + 1):
        out.append(inner + r * i / float(k))
    # 중복 제거
    res = []
    for x in out:
        if not res or abs(x - res[-1]) > 1e-6:
            res.append(x)
    return res


def rounded_box(c, size, r, k=5, m=2):
    """중심 c, 크기 size=(lx,ly,lz), 모서리 반경 r 인 라운드 박스."""
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    r = max(0.5, min(r, hx - 0.1, hy - 0.1, hz - 0.1))
    inner = (hx - r, hy - r, hz - r)
    H = (hx, hy, hz)
    mesh = Mesh()
    for w in range(3):
        u, v = (w + 1) % 3, (w + 2) % 3
        su, sv = _samples(H[u], r, k, m), _samples(H[v], r, k, m)
        for sign in (1, -1):
            base = len(mesh.v)
            for a in su:
                for b in sv:
                    P = [0, 0, 0]
                    P[u], P[v], P[w] = a, b, sign * H[w]
                    Q = [max(-inner[i], min(inner[i], P[i])) for i in range(3)]
                    dv = [P[i] - Q[i] for i in range(3)]
                    L = math.sqrt(sum(x * x for x in dv)) or 1.0
                    mesh.v.append(tuple(c[i] + Q[i] + r * dv[i] / L for i in range(3)))
            nv = len(sv)
            for i in range(len(su) - 1):
                for j in range(nv - 1):
                    a0 = base + i * nv + j
                    q = (a0, a0 + nv, a0 + nv + 1, a0 + 1)
                    mesh.f.append(q if sign > 0 else q[::-1])
    return mesh


def revolve(profile, seg=36):
    """profile [(r,z)] 를 Z축 회전. 반경 0 점은 극점."""
    mesh = Mesh()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            ring.append(len(mesh.v))
            mesh.v.append((r * math.cos(t), r * math.sin(t), z))
        rings.append(ring)
    for a in range(len(rings) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            mesh.f.append((rings[a][i], rings[a][j], rings[a + 1][j], rings[a + 1][i]))
    return mesh


def orient(mesh, origin, direction):
    """Z축 메시를 direction 방향으로 회전 후 origin 으로 이동."""
    dx, dy, dz = direction
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    dx, dy, dz = dx / L, dy / L, dz / L
    # Rodrigues: z -> d
    kx, ky, kz = -dy, dx, 0.0
    s = math.sqrt(kx * kx + ky * ky)
    c = dz
    if s < 1e-9:
        R_ = [[1, 0, 0], [0, 1, 0], [0, 0, 1]] if c > 0 else [[1, 0, 0], [0, -1, 0], [0, 0, -1]]
    else:
        kx, ky = kx / s, ky / s
        K = [[0, -kz, ky], [kz, 0, -kx], [-ky, kx, 0]]
        K2 = [[sum(K[i][m] * K[m][j] for m in range(3)) for j in range(3)] for i in range(3)]
        R_ = [[(1 if i == j else 0) + s * K[i][j] + (1 - c) * K2[i][j] for j in range(3)] for i in range(3)]
    ox, oy, oz = origin
    return mesh.map(lambda p: (ox + R_[0][0] * p[0] + R_[0][1] * p[1] + R_[0][2] * p[2],
                               oy + R_[1][0] * p[0] + R_[1][1] * p[1] + R_[1][2] * p[2],
                               oz + R_[2][0] * p[0] + R_[2][1] * p[1] + R_[2][2] * p[2]))


def cylinder(center, axis, r, length, seg=36, fillet=0.0):
    h = length / 2.0
    if fillet > 0:
        prof = [(0, -h), (r - fillet, -h)]
        for i in range(1, 5):
            t = math.pi / 2 * i / 4
            prof.append((r - fillet + fillet * math.sin(t), -h + fillet - fillet * math.cos(t)))
        for i in range(0, 5):
            t = math.pi / 2 * i / 4
            prof.append((r - fillet + fillet * math.cos(t), h - fillet + fillet * math.sin(t)))
        prof.append((0, h))
    else:
        prof = [(0, -h), (r, -h), (r, h), (0, h)]
    return orient(revolve(prof, seg), center, axis)


def ring(center, axis, r_in, r_out, length, seg=36):
    h = length / 2.0
    prof = [(r_in, -h), (r_out, -h), (r_out, h), (r_in, h), (r_in, -h)]
    return orient(revolve(prof, seg), center, axis)


def tire(center, axis, R_, width, seg=48):
    h = width / 2.0
    rr = h * 0.9
    prof = [(R_ - 2.2 * rr, -h * 0.8)]
    for i in range(0, 9):
        t = -math.pi / 2 + math.pi * i / 8
        prof.append((R_ - rr + rr * math.cos(t), rr * math.sin(t)))
    prof.append((R_ - 2.2 * rr, h * 0.8))
    prof.append((R_ - 2.2 * rr, -h * 0.8))
    return orient(revolve(prof, seg), center, axis)


def ellipsoid(c, rx, ry, rz, seg=28, rings_=16):
    prof = [(math.sin(math.pi * i / rings_), -math.cos(math.pi * i / rings_)) for i in range(rings_ + 1)]
    m = revolve(prof, seg)
    return m.map(lambda p: (c[0] + p[0] * rx, c[1] + p[1] * ry, c[2] + p[2] * rz))


def capsule(p1, p2, r1, r2, seg=20):
    L = math.sqrt(sum((p2[i] - p1[i]) ** 2 for i in range(3)))
    prof = []
    for i in range(0, 7):
        t = -math.pi / 2 + math.pi / 2 * i / 6
        prof.append((r1 * math.cos(t), r1 * math.sin(t)))
    for i in range(0, 7):
        t = math.pi / 2 * i / 6
        prof.append((r2 * math.cos(t), L + r2 * math.sin(t)))
    return orient(revolve(prof, seg), p1, tuple(p2[i] - p1[i] for i in range(3)))


# =============================================================================
# 5. 파트 생성
# =============================================================================
def ov(part, key, default):
    return OVERRIDES.get(part, {}).get(key, default)


class Part(object):
    def __init__(self, name):
        self.name = name
        self.items = []    # (Mesh, color, sublabel)

    def add(self, mesh, color, label=""):
        self.items.append((mesh, COLORS[color] if isinstance(color, str) else color, label))

    def bbox(self):
        lo, hi = [1e9] * 3, [-1e9] * 3
        for m, _, _ in self.items:
            a, b = m.bbox()
            lo = [min(lo[i], a[i]) for i in range(3)]
            hi = [max(hi[i], b[i]) for i in range(3)]
        return tuple(lo), tuple(hi)


def seat_z(d, x):
    """압축 좌면 높이 at x"""
    sx = d.v["seat_rear_x"]
    return d.v["seat_rear_h"] + (x - sx) * math.tan(math.radians(R("seat_tilt_deg")))


def back_frame(d):
    """등받이 기준선: 원점(좌석후단, 압축좌면), b=등받이 방향 단위벡터, n=전방 법선"""
    rec = math.radians(R("back_recline_deg"))
    b = (-math.sin(rec), math.cos(rec))
    n = (math.cos(rec), math.sin(rec))
    o = (d.v["seat_rear_x"], d.v["seat_rear_h"])
    return o, b, n


def bpt(d, s, t):
    o, b, n = back_frame(d)
    return (o[0] + b[0] * s + n[0] * t, o[1] + b[1] * s + n[1] * t)


def build_parts(d, poses=True):
    P = {}
    sx, sd, sw = d.v["seat_rear_x"], d.v["seat_depth"], d.v["seat_width"]
    tilt, rec = R("seat_tilt_deg"), R("back_recline_deg")
    sr = d.v["seat_rear_h"]
    comp = R("cushion_compress")

    # 1 Seat Cushion (비압축 형상) -------------------------------------------
    p = Part("Seat Cushion")
    thk = ov(p.name, "thk", R("cushion_thk"))
    w = ov(p.name, "w", sw)
    dep = ov(p.name, "d", sd)
    top_unc = sr + comp
    m = rounded_box((sx + dep / 2.0, 0, top_unc - thk / 2.0), (dep, w, thk), R("front_round_r"))
    m.rot_y(tilt, sx, top_unc)
    p.add(m, "fabric", "cushion")
    pan = rounded_box((sx + dep / 2.0 - 10, 0, top_unc - thk - 15), (dep + 40, w - 10, 30), 10)
    pan.rot_y(tilt, sx, top_unc)
    p.add(pan, "graphite", "seat pan")
    P[p.name] = p

    # 2 Backrest -------------------------------------------------------------
    p = Part("Backrest")
    bh = ov(p.name, "h", d.v["back_height"])
    bw = ov(p.name, "w", d.v["back_width"])
    ct = R("back_cushion_thk")
    st = R("back_shell_thk")
    m = rounded_box((0, 0, 0), (ct, bw, bh + 40), 25)       # 쿠션: 등받이 기준선 뒤쪽
    m.move(-ct / 2.0, 0, (bh + 40) / 2.0 - 40)
    m.rot_y(rec, 0, 0).move(sx, 0, sr)
    p.add(m, "fabric", "back cushion")
    sh = rounded_box((0, 0, 0), (st, bw + 30, bh + 80), 15)
    sh.move(-ct - st / 2.0, 0, (bh + 80) / 2.0 - 70)
    sh.rot_y(rec, 0, 0).move(sx, 0, sr)
    p.add(sh, "white", "back shell")
    # 측면 실버 프레임 라인
    for sgn in (1, -1):
        fr = rounded_box((0, 0, 0), (st + 10, 12, bh + 60), 5)
        fr.move(-ct - st / 2.0, sgn * (bw / 2.0 + 15), (bh + 60) / 2.0 - 60)
        fr.rot_y(rec, 0, 0).move(sx, 0, sr)
        p.add(fr, "silver", "frame")
    P[p.name] = p

    # 3 Headrest -------------------------------------------------------------
    p = Part("Headrest")
    hw = ov(p.name, "w", d.v["headrest_w"])
    hh = ov(p.name, "h", d.v["headrest_h"])
    ht = ov(p.name, "t", d.v["headrest_t"])
    hc = ov(p.name, "center_s", d.v["headrest_center_s"])
    fo = ov(p.name, "fwd", d.v["headrest_fwd_offset"])
    m = rounded_box((0, 0, 0), (ht, hw, hh), 30)
    m.move(fo - ht / 2.0, 0, hc).rot_y(rec, 0, 0).move(sx, 0, sr)
    p.add(m, "fabric", "pad")
    sh = rounded_box((0, 0, 0), (25, hw + 16, hh + 16), 12)
    sh.move(fo - ht - 10, 0, hc).rot_y(rec, 0, 0).move(sx, 0, sr)
    p.add(sh, "white", "shell")
    for sgn in (1, -1):    # 스템
        stem = rounded_box((0, 0, 0), (18, 18, hc - hh / 2.0 - bh + 40), 8)
        stem.move(-ct - st / 2.0 + 5, sgn * 70, bh - 20 + (hc - hh / 2.0 - bh + 40) / 2.0)
        stem.rot_y(rec, 0, 0).move(sx, 0, sr)
        p.add(stem, "silver", "stem")
    P[p.name] = p

    # 4,5 Armrests -----------------------------------------------------------
    ai = d.v["armrest_inner_gap"]
    at = d.v["armrest_top_abs"]
    for side, sgn in (("Left Armrest", 1), ("Right Armrest", -1)):
        p = Part(side)
        L = ov(side, "len", d.v["armrest_len"])
        pw_ = ov(side, "pad_w", d.v["armrest_pad_w"])
        sw_ = R("arm_struct_w")
        yc = sgn * (ai / 2.0 + sw_ / 2.0)
        x0 = sx + 40 - 60
        # 구조 암 (화이트) — 등받이 측면에서 전방까지
        arm = rounded_box((x0 + (L + 90) / 2.0 - 20, yc, at - R("arm_pad_h") - 22), (L + 90, sw_, 44), 18)
        p.add(arm, "white", "arm structure")
        pad = rounded_box((x0 + L / 2.0 + 30, yc - sgn * 2, at - R("arm_pad_h") / 2.0), (L, pw_, R("arm_pad_h")), 16)
        p.add(pad, "fabric", "arm pad")
        # 전면 수직 포스트 (곡선 연결)
        fx = x0 + L + 50
        post_h = at - R("arm_pad_h") - 22 - (sr - 60)
        post = rounded_box((fx, yc, sr - 60 + post_h / 2.0), (60, sw_ - 10, post_h + 20), 22)
        p.add(post, "white", "front post")
        led = rounded_box((fx + 30, yc, at - 120), (4, 10, 50), 2)
        p.add(led, "accent", "LED")
        if sgn < 0:   # 조이스틱 (오른쪽)
            jx = sx + d.v["joystick_from_back"]
            jy = yc
            p.add(cylinder((jx, jy, at + 5), (0, 0, 1), 22, 14), "graphite", "joystick base")
            p.add(capsule((jx, jy, at + 10), (jx, jy, at + 55), 7, 7, 12), "silver", "joystick stick")
            p.add(ellipsoid((jx, jy, at + 65), 15, 15, 18), (180, 110, 60), "joystick knob")
        P[side] = p

    # 6 Side Body ------------------------------------------------------------
    p = Part("Side Body")
    rR = R("rear_D") / 2.0
    y_rw, rW = d.v["y_rw"], R("rear_W")
    t_sb = ov(p.name, "thk", 70)
    y_sb = ai / 2.0 + R("arm_struct_w") - t_sb / 2.0
    xf = d.v["seat_front_x"] + 30
    zb_front = R("caster_D") + 40
    x_wheel_front = rR + R("wheel_body_clear")
    z_top = sr - 35
    for sgn in (1, -1):
        upper = rounded_box(((sx - 110 + xf) / 2.0, sgn * y_sb, (2 * rR + 25 + z_top) / 2.0),
                            (xf - (sx - 110), t_sb, z_top - (2 * rR + 25)), 28)
        p.add(upper, "white", "upper rail")
        lower = rounded_box(((x_wheel_front + xf) / 2.0, sgn * y_sb, (zb_front + z_top) / 2.0 - 10),
                            (xf - x_wheel_front, t_sb, z_top - zb_front - 20), 30)
        p.add(lower, "white", "front panel")
        p.add(rounded_box((xf - 30, sgn * (y_sb + t_sb / 2.0), (zb_front + z_top) / 2.0), (60, 4, 10), 1.5),
              "accent", "badge")
    P[p.name] = p

    # 7 Lower Chassis --------------------------------------------------------
    p = Part("Lower Chassis")
    gc = R("ground_clear")
    yi = y_rw - rW / 2.0 - R("wheel_body_clear")
    xs, env = d.v["caster_swivel_x"], d.v["caster_swivel_envelope_r"]
    x_back = ov(p.name, "x_back", -rR + 20)
    x_front = ov(p.name, "x_front", xs - env - R("wheel_body_clear"))
    z_top_c = sr - R("cushion_thk") - 30 - 10
    m = rounded_box(((x_back + x_front) / 2.0, 0, (gc + z_top_c) / 2.0), (x_front - x_back, 2 * yi, z_top_c - gc), 35)
    p.add(m, "white", "battery/drive box")
    p.add(rounded_box(((x_back + x_front) / 2.0, 0, gc + 12), (x_front - x_back - 30, 2 * yi + 4, 24), 10),
          "graphite", "skid")
    # 후륜 모터/차축 하우징
    p.add(cylinder((0, 0, rR), (0, 1, 0), 45, 2 * (y_rw - rW / 2.0) - 4, 24), "graphite", "axle")
    # 캐스터 아웃리거
    for sgn in (1, -1):
        p.add(rounded_box(((x_front + xs) / 2.0 + 20, sgn * (d.v["y_c"] + 0) * 0.98, R("caster_D") + 55),
                          (xs - x_front + 60, 50, 40), 15), "silver", "caster outrigger")
    P[p.name] = p

    # 8 Rear Wheels ----------------------------------------------------------
    p = Part("Rear Wheels")
    for sgn in (1, -1):
        c = (0, sgn * y_rw, rR)
        p.add(tire(c, (0, 1, 0), rR, rW), "tire", "tire")
        p.add(cylinder(c, (0, 1, 0), rR * 0.68, rW * 0.9, 48, fillet=8), "white", "hub cover")
        p.add(ring((0, sgn * (y_rw + rW * 0.45), rR), (0, 1, 0), rR * 0.70, rR * 0.73, 3, 48), "accent", "LED ring")
    P[p.name] = p

    # 9 Front Casters --------------------------------------------------------
    p = Part("Front Casters")
    cR, cW, tr = R("caster_D") / 2.0, R("caster_W"), R("caster_trail")
    for sgn in (1, -1):
        y = sgn * d.v["y_c"]
        c = (xs - tr, y, cR)
        p.add(tire(c, (0, 1, 0), cR, cW, 36), "tire", "tire")
        p.add(cylinder(c, (0, 1, 0), cR * 0.62, cW * 0.92, 36, fillet=5), "white", "hub")
        p.add(ring((c[0], y + sgn * cW * 0.47, cR), (0, 1, 0), cR * 0.64, cR * 0.68, 2, 36), "accent", "LED")
        for fs in (1, -1):
            p.add(rounded_box(((xs + c[0]) / 2.0, y + fs * (cW / 2.0 + 8), (cR + 2 * cR + 30) / 2.0),
                              (tr + 40, 10, cR + 50), 5), "silver", "fork")
        p.add(cylinder((xs, y, 2 * cR + 40), (0, 0, 1), 18, 40), "graphite", "swivel")
    P[p.name] = p

    # 10 Rehabilitation Mechanism (공통 차체: 중앙 스파인 + 캐리지) ------------
    p = Part("Rehabilitation Mechanism")
    heel = d.v["plate_heel_x"]
    pt = d.v["plate_top_h"]
    sp_w = ov(p.name, "spine_w", R("spine_w"))
    sp_x0 = x_front - 30
    sp_x1 = heel - 25
    sp_z0 = gc
    sp_z1 = ov(p.name, "spine_top", 170)
    p.add(rounded_box(((sp_x0 + sp_x1) / 2.0, 0, (sp_z0 + sp_z1) / 2.0), (sp_x1 - sp_x0, sp_w, sp_z1 - sp_z0), 20),
          "graphite", "spine housing")
    # 캐리지 블록(발판 뒤꿈치 하부, 발판 최저 지상고 유지)
    p.add(rounded_box((heel + 30, 0, (gc - 15 + pt - R("plate_thk")) / 2.0 + 5), (110, sp_w - 10, 40), 10),
          "silver", "carriage")
    # 경사 레일(슬라이딩 옵션 시) 커버
    # 수직 리프트 하우징 (좌석 전면 하부)
    p.add(rounded_box((d.v["seat_front_x"] - 40, 0, (gc + sr - 60) / 2.0 + 20), (90, 140, sr - 60 - gc - 40), 25),
          "white", "front riser")
    # 캐리지 크로스바
    p.add(rounded_box((heel + 60, 0, pt - R("plate_thk") - 6), (60, 2 * d.v["plate_center_y"], 12), 5),
          "silver", "carriage bar")
    P[p.name] = p

    # 11,12 Foot Platforms ---------------------------------------------------
    pl, pw = d.v["plate_len"], d.v["plate_w"]
    pyc = d.v["plate_center_y"]
    for side, sgn in (("Left Foot Platform", 1), ("Right Foot Platform", -1)):
        p = Part(side)
        P[side] = p
        for mm, col, lab in foot_platform(heel, sgn * pyc, pt, pl, pw, sgn):
            p.add(mm, col, lab)

    # 13 Human Reference -----------------------------------------------------
    p = Part("Human Reference")
    for mm, lab in human_dummy(d, d.v["ankle"]):
        p.add(mm, "human", lab)
    P[p.name] = p

    # 재활 자세(참조용, 별도 레이어)
    extra = {}
    if poses:
        if d.v.get("slide"):
            s = d.v["slide"]
            g = Part("Rehab Pose - Slide end")
            for mm, lab in legs_only(d, s["end_ankle"]):
                g.add(mm, "ghost", lab)
            T = s["end_ankle"]
            hx = T[0] - Lk("ankle_fwd_of_heel")
            ptz = T[1] - Lk("ankle_above_sole")
            for sgn in (1, -1):
                for mm, col, lab in foot_platform(hx, sgn * pyc, ptz, pl, pw, sgn):
                    g.add(mm, "ghost", lab)
            ang, Lr = s["angle"], s["stroke"] + 100
            rail = rounded_box((0, 0, 0), (Lr, 60, 30), 12)
            rail.move(Lr / 2.0, 0, 0).rot_y(ang, 0, 0).move(heel + 30, 0, 65)
            g.add(rail, "ghost", "inclined rail (slide option)")
            extra[g.name] = g
        if d.v.get("pedal"):
            pe = d.v["pedal"]
            g = Part("Rehab Pose - Pedal")
            for k, ph in enumerate((0, 90, 180, 270)):
                a = math.radians(ph)
                px, pz = pe["cx"] + pe["r"] * math.cos(a), pe["cz"] + pe["r"] * math.sin(a)
                T = (px - 30, pz + Lk("ankle_above_sole") - 10)
                if ph in (0, 180):
                    for mm, lab in legs_only(d, T, sides=(1,) if ph == 0 else (-1,)):
                        g.add(mm, "ghost2", lab)
            g.add(cylinder((pe["cx"], 0, pe["cz"]), (0, 1, 0), 40, 2 * pyc + 40, 24), "ghost2", "crank hub")
            for sgn in (1, -1):
                g.add(ring((pe["cx"], sgn * pyc, pe["cz"]), (0, 1, 0), pe["r"] - 3, pe["r"] + 3, 6, 48),
                      "ghost2", "pedal path")
            extra[g.name] = g
    return P, extra


def foot_platform(heel_x, yc, top, pl, pw, sgn):
    out = []
    t = R("plate_thk")
    out.append((rounded_box((heel_x + pl / 2.0, yc, top - t / 2.0), (pl, pw, t), 8), "white", "plate"))
    out.append((rounded_box((heel_x + pl / 2.0 + 10, yc, top + 2), (pl - 40, pw - 20, 4), 2), "graphite", "grip mat"))
    hl = R("heel_loop_h")
    out.append((rounded_box((heel_x - 8, yc, top + hl / 2.0), (16, pw, hl), 6), "silver", "heel loop"))
    out.append((rounded_box((heel_x + pl * 0.45, yc + sgn * (pw / 2.0 + 6), top + R("side_guard_h") / 2.0),
                            (pl * 0.8, 12, R("side_guard_h")), 5), "white", "outer guard"))
    out.append((rounded_box((heel_x + pl * 0.62, yc, top + 55), (60, pw + 4, 6), 3), "graphite", "instep strap"))
    out.append((rounded_box((heel_x + pl - 15, yc, top - t - 1), (6, pw - 30, 2), 1), "accent", "LED"))
    return out


def legs_only(d, ankle, sides=(1, -1)):
    out = []
    hip = d.v["hip"]
    r = ik_2link(hip, ankle, d.v["L1"], d.v["L2"])
    if r is None:
        return out
    K = r[0]
    hy = A("앉은엉덩이너비") / 4.0
    for sgn in sides:
        y = sgn * hy
        out.append((capsule((hip[0], y, hip[1]), (K[0], y, K[1]), A("앉은넙다리높이") / 2.0, 55), "thigh"))
        out.append((capsule((K[0], y, K[1]), (ankle[0], y, ankle[1]), 48, 35), "shank"))
        fl, fw = A("발길이"), A("발너비")
        heel = ankle[0] - Lk("ankle_fwd_of_heel")
        sole = ankle[1] - Lk("ankle_above_sole")
        out.append((rounded_box((heel + fl / 2.0, y, sole + 40), (fl, fw, 80), 30), "foot+shoe"))
    return out


def human_dummy(d, ankle):
    """파라메트릭 착석 더미 (사이즈코리아 3D 스캔 아님)."""
    out = legs_only(d, ankle)
    sx, sr = d.v["seat_rear_x"], d.v["seat_rear_h"]
    rec = R("back_recline_deg")
    td = Lk("torso_depth")
    hipw = A("앉은엉덩이너비")
    # 골반
    pel = rounded_box((sx + 115, 0, sr + 75), (230, hipw, 150), 60)
    out.append((pel, "pelvis"))
    # 몸통 (등받이면에 접촉)
    sh = A("앉은어깨높이")
    torso = rounded_box((0, 0, 0), (td, A("어깨너비") + 20, sh - 120), 80)
    torso.move(td / 2.0, 0, 120 + (sh - 120) / 2.0 - 30).rot_y(rec, 0, 0).move(sx, 0, sr)
    out.append((torso, "torso"))
    # 목·머리
    neck_b = bpt(d, sh - 20, 95)
    occ_s = A("앉은키") - Lk("occiput_below_vertex")
    head_c = bpt(d, occ_s + 10, Lk("occiput_fwd_of_back") + A("머리길이") / 2.0)
    out.append((capsule((neck_b[0], 0, neck_b[1]), (head_c[0] - 10, 0, head_c[1] - 60), 50, 45), "neck"))
    out.append((ellipsoid((head_c[0], 0, head_c[1]), A("머리길이") / 2.0, A("머리너비") / 2.0,
                          A("머리수직길이") / 2.0), "head"))
    # 팔: 어깨관절 → 팔꿈치(팔걸이 위) → 손
    sj = bpt(d, sh - 40, 90)
    ez = d.v["armrest_top_abs"] + 38          # 전완이 팔걸이 패드 위에 놓임
    ex = sx + 100
    for sgn in (1, -1):
        y_s = sgn * (A("어깨너비") / 2.0 - 10)
        y_e = sgn * (d.v["armrest_inner_gap"] / 2.0 + 30)
        out.append((capsule((sj[0], y_s, sj[1]), (ex, y_e, ez), 45, 38), "upper arm"))
        wx = ex + A("팔꿈치손목길이")
        out.append((capsule((ex, y_e, ez), (wx, y_e, ez + 10), 38, 28), "forearm"))
        out.append((ellipsoid((wx + 50, y_e, ez + 10), 55, 25, 40), "hand"))
    return out


# =============================================================================
# 6. 검사 (기준점 / 바운딩박스 / 간섭)
# =============================================================================
def aabb_overlap(a, b, tol=0.0):
    (al, ah), (bl, bh) = a, b
    ov_ = [min(ah[i], bh[i]) - max(al[i], bl[i]) for i in range(3)]
    return ov_ if all(x > tol for x in ov_) else None


EXPECTED_CONTACT = {
    frozenset(["Seat Cushion", "Human Reference"]): "쿠션 압축량 만큼 의도된 겹침(착석)",
    frozenset(["Backrest", "Human Reference"]): "등 접촉(의도)",
    frozenset(["Headrest", "Human Reference"]): "후두부 접촉(의도)",
    frozenset(["Left Armrest", "Human Reference"]): "팔꿈치 지지(의도)",
    frozenset(["Right Armrest", "Human Reference"]): "팔꿈치 지지(의도)",
    frozenset(["Left Foot Platform", "Human Reference"]): "발 접촉(의도)",
    frozenset(["Right Foot Platform", "Human Reference"]): "발 접촉(의도)",
}


def seg_box_dist(p1, p2, lo, hi, n=40):
    best = 1e9
    for i in range(n + 1):
        t = i / float(n)
        q = [p1[k] + (p2[k] - p1[k]) * t for k in range(3)]
        dv = [max(lo[k] - q[k], 0, q[k] - hi[k]) for k in range(3)]
        best = min(best, math.sqrt(sum(x * x for x in dv)))
    return best


def checks(d, P):
    res = []
    # 바운딩박스 쌍 겹침 (거친 검사 — 실제 형상 간섭은 Rhino MeshMeshFast 로 재확인)
    names = [n for n in PART_ORDER if n in P]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            o = aabb_overlap(P[names[i]].bbox(), P[names[j]].bbox(), 1.0)
            if o:
                key = frozenset([names[i], names[j]])
                res.append(("BBox", names[i] + " ↔ " + names[j],
                            "겹침 %.0f×%.0f×%.0f" % tuple(o), EXPECTED_CONTACT.get(key, "형상 간섭 정밀검사 필요")))
    # 캐스터 궤적 ↔ 발판
    gap = d.v["plate_heel_x"] - 8 - (d.v["caster_swivel_x"] + d.v["caster_swivel_envelope_r"])
    res.append(("Clearance", "발판 뒤꿈치지지대 ↔ 캐스터 회전궤적(평면)", "%.0f mm" % gap, "OK" if gap >= 15 else "NG"))
    res.append(("Clearance", "발판 최저 지상고(기본자세)", "%.0f mm" % d.v["plate_bottom_h"],
                "OK" if d.v["plate_bottom_h"] >= 50 else "NG"))
    res.append(("Clearance", "무릎 뒤 여유 P50 / P5", "%.0f / %.0f mm" % (d.v["knee_clear_P50"], d.v["knee_clear_P5"]),
                "OK" if d.v["knee_clear_P5"] >= 25 else "검토"))
    res.append(("Width", "전폭", "%.0f mm" % d.v["overall_width"], "OK" if d.v["overall_width"] <= R("max_width") else "초과"))
    # 재활 자세 다리 ↔ 차체
    hip = d.v["hip"]
    bodies = {}
    for n in ("Front Casters", "Rehabilitation Mechanism", "Side Body", "Lower Chassis"):
        for m, _, lab in P[n].items:
            bodies[n + "/" + lab + "#%d" % len(bodies)] = m.bbox()
    poses = [("기본자세", d.v["ankle"])]
    if d.v.get("slide"):
        poses.append(("슬라이딩 신전 끝", d.v["slide"]["end_ankle"]))
    if d.v.get("pedal"):
        pe = d.v["pedal"]
        for ph in (0, 90, 180, 270):
            a = math.radians(ph)
            poses.append(("페달 %d°" % ph, (pe["cx"] + pe["r"] * math.cos(a) - 30,
                                            pe["cz"] + pe["r"] * math.sin(a) + Lk("ankle_above_sole") - 10)))
    for nm, T in poses:
        r = ik_2link(hip, T, d.v["L1"], d.v["L2"])
        if r is None:
            res.append(("Rehab", nm, "IK 불가", "NG")); continue
        K, kn, th = r
        y = A("앉은엉덩이너비") / 4.0
        dmin, who = 1e9, ""
        for bn, (lo, hi) in bodies.items():
            dd = seg_box_dist((K[0], y, K[1]), (T[0], y, T[1]), lo, hi) - 48
            if dd < dmin:
                dmin, who = dd, bn
        # 허벅지 하면 ↔ 좌석 전단
        res.append(("Rehab", "%s: 무릎 %.0f°, 허벅지 %.0f°" % (nm, kn, th),
                    "정강이↔%s 최소 %.0f mm (부품별 AABB 근사)" % (who.split("#")[0], dmin), "OK" if dmin >= 10 else "검토"))
    return res


def reference_points(d):
    pts = {
        "ORIGIN (floor, rear axle)": (0, 0, 0),
        "Rear axle": (0, 0, R("rear_D") / 2.0),
        "Seat rear (compressed)": (d.v["seat_rear_x"], 0, d.v["seat_rear_h"]),
        "Seat front (compressed)": (d.v["seat_front_x"], 0, d.v["seat_front_h"]),
        "Hip joint": (d.v["hip"][0], 0, d.v["hip"][1]),
        "Knee joint": (d.v["knee"][0], 0, d.v["knee"][1]),
        "Ankle joint": (d.v["ankle"][0], 0, d.v["ankle"][1]),
        "Caster swivel L": (d.v["caster_swivel_x"], d.v["y_c"], R("caster_D") + 40),
        "Lumbar center": tuple([bpt(d, d.v["lumbar_center"], 0)[0], 0, bpt(d, d.v["lumbar_center"], 0)[1]]),
        "Headrest center": tuple([bpt(d, d.v["headrest_center_s"], d.v["headrest_fwd_offset"])[0], 0,
                                  bpt(d, d.v["headrest_center_s"], d.v["headrest_fwd_offset"])[1]]),
        "Joystick": (d.v["seat_rear_x"] + d.v["joystick_from_back"], -(d.v["armrest_inner_gap"] / 2.0 + 40),
                     d.v["armrest_top_abs"] + 60),
    }
    if d.v.get("pedal"):
        pts["Crank center"] = (d.v["pedal"]["cx"], 0, d.v["pedal"]["cz"])
    return pts


def build_all(folder=None):
    if folder:
        load_sizekorea_override(folder)
    d = derive()
    P, extra = build_parts(d)
    return d, P, extra


# =============================================================================
# 7. Rhino 8 실행부 (RhinoCommon)
# =============================================================================
def run_in_rhino():
    import Rhino
    import scriptcontext as sc
    import System
    doc = sc.doc
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        folder = None
    d, P, extra = build_all(folder)
    doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    root = "Rehab Wheelchair"

    def layer(name, col):
        full = root + "::" + name
        idx = doc.Layers.FindByFullPath(full, -1)
        if idx < 0:
            parent = doc.Layers.FindByFullPath(root, -1)
            if parent < 0:
                parent = doc.Layers.Add(root, System.Drawing.Color.Black)
            L = Rhino.DocObjects.Layer()
            L.Name = name
            L.ParentLayerId = doc.Layers[parent].Id
            L.Color = System.Drawing.Color.FromArgb(*col)
            idx = doc.Layers.Add(L)
        return idx

    rh_meshes = {}
    for name, part in list(P.items()) + list(extra.items()):
        li = layer(name, part.items[0][1])
        rh_meshes[name] = []
        for m, col, lab in part.items:
            rm = Rhino.Geometry.Mesh()
            for v in m.v:
                rm.Vertices.Add(v[0], v[1], v[2])
            for f in m.f:
                if len(f) == 4:
                    rm.Faces.AddFace(f[0], f[1], f[2], f[3])
                else:
                    rm.Faces.AddFace(f[0], f[1], f[2])
            rm.Vertices.CombineIdentical(True, True)
            rm.Normals.ComputeNormals()
            rm.Compact()
            at = Rhino.DocObjects.ObjectAttributes()
            at.LayerIndex = li
            at.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
            at.ObjectColor = System.Drawing.Color.FromArgb(*col)
            at.Name = name + " / " + lab
            doc.Objects.AddMesh(rm, at)
            rh_meshes[name].append(rm)
    # 기준점
    li = layer("_Reference Points", (255, 0, 0))
    for k, p in reference_points(d).items():
        at = Rhino.DocObjects.ObjectAttributes(); at.LayerIndex = li
        doc.Objects.AddTextDot(k, Rhino.Geometry.Point3d(*p), at)
    # 바운딩박스
    li = layer("_Bounding Boxes", (150, 150, 150))
    for name, part in P.items():
        lo, hi = part.bbox()
        bb = Rhino.Geometry.BoundingBox(Rhino.Geometry.Point3d(*lo), Rhino.Geometry.Point3d(*hi))
        at = Rhino.DocObjects.ObjectAttributes(); at.LayerIndex = li; at.Name = "BBox " + name
        doc.Objects.AddBrep(Rhino.Geometry.Brep.CreateFromBox(bb), at)
        doc.Layers[li].IsVisible = False
    # 정밀 간섭 (MeshMeshFast)
    li = layer("_Interference", (255, 0, 0))
    print("=== MeshMesh 간섭 검사 ===")
    names = [n for n in PART_ORDER if n in rh_meshes]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            hits = 0
            for ma in rh_meshes[a]:
                for mb in rh_meshes[b]:
                    bb = Rhino.Geometry.BoundingBox.Intersection(ma.GetBoundingBox(False), mb.GetBoundingBox(False))
                    if not bb.IsValid:
                        continue
                    lines = Rhino.Geometry.Intersect.Intersection.MeshMeshFast(ma, mb)
                    if lines:
                        hits += len(lines)
                        for ln in lines:
                            at = Rhino.DocObjects.ObjectAttributes(); at.LayerIndex = li
                            doc.Objects.AddLine(ln, at)
            if hits:
                tag = EXPECTED_CONTACT.get(frozenset([a, b]), "확인 필요")
                print("%s <-> %s : %d 교차선 (%s)" % (a, b, hits, tag))
    print("=== 치수 검사 ===")
    for r in checks(d, P):
        print(" | ".join(r))
    doc.Views.Redraw()


if __name__ == "__main__":
    try:
        import Rhino  # noqa
        IN_RHINO = True
    except ImportError:
        IN_RHINO = False
    if IN_RHINO:
        run_in_rhino()
    else:
        d, P, extra = build_all(os.path.dirname(os.path.abspath(__file__)))
        for r in d.rows:
            print(r)
