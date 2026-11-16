# -*- coding: utf-8 -*-
"""
Rhino 없이 실행: wc_model 로 1:1 모델을 만들어
  * out/RehabWheelchair_170cm_1to1.3dm   (rhino3dm, mm, 파트별 레이어)
  * out/views_*.png                       (정면/측면/평면/사시)
  * out/seating_*.png                     (착석·재활 자세 검토)
  * out/dims.csv, out/checks.csv, out/parts_bbox.csv
사용:  pip install rhino3dm matplotlib && python export_and_render.py
"""
import os
import csv
import math
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wc_model as W  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

d, P, EXTRA = W.build_all(HERE)


# ---------------------------------------------------------------- 3dm export
def export_3dm(path):
    import rhino3dm as r3
    f = r3.File3dm()
    f.Settings.ModelUnitSystem = r3.UnitSystem.Millimeters
    root = r3.Layer(); root.Name = "Rehab Wheelchair"
    f.Layers.Add(root)
    root_id = f.Layers[0].Id

    def add_layer(name, col):
        L = r3.Layer(); L.Name = name; L.ParentLayerId = root_id
        L.Color = (col[0], col[1], col[2], 255)
        return f.Layers.Add(L)

    for name, part in list(P.items()) + list(EXTRA.items()):
        li = add_layer(name, part.items[0][1])
        for m, col, lab in part.items:
            rm = r3.Mesh()
            for v in m.v:
                rm.Vertices.Add(v[0], v[1], v[2])
            for fc in m.f:
                rm.Faces.AddFace(*fc)
            rm.Normals.ComputeNormals()
            rm.Compact()
            at = r3.ObjectAttributes()
            at.LayerIndex = li
            at.ColorSource = r3.ObjectColorSource.ColorFromObject
            at.ObjectColor = (col[0], col[1], col[2], 255)
            at.Name = name + " / " + lab
            f.Objects.AddMesh(rm, at)
    li = add_layer("_Reference Points", (255, 0, 0))
    for k, p in W.reference_points(d).items():
        at = r3.ObjectAttributes(); at.LayerIndex = li
        f.Objects.AddTextDot(k, r3.Point3d(*p), at)
    li = add_layer("_Bounding Boxes", (150, 150, 150))
    for name, part in P.items():
        lo, hi = part.bbox()
        bb = r3.BoundingBox(r3.Point3d(*lo), r3.Point3d(*hi))
        at = r3.ObjectAttributes(); at.LayerIndex = li; at.Name = "BBox " + name
        f.Objects.AddBrep(r3.Brep.CreateFromBox(r3.Box(bb)), at)
    f.Write(path, 8)
    return path


# ---------------------------------------------------------------- renderer
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib import font_manager  # noqa: E402

for fp in ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
           "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


def norm(v):
    L = math.sqrt(sum(x * x for x in v)) or 1
    return tuple(x / L for x in v)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


VIEWS = {
    "front": (-1, 0, 0),         # 카메라 +X 에서 -X 방향
    "side": (0, 1, 0),           # 카메라 -Y(오른쪽)에서 +Y 방향 → 전방이 화면 오른쪽
    "top": (0, 0, -1),
    "persp": norm((-1, 0.85, -0.55)),
}


def view_basis(fwd):
    up0 = (0, 0, 1) if abs(fwd[2]) < 0.99 else (0, 1, 0)
    right = norm(cross(fwd, up0))
    up = cross(right, fwd)
    if fwd == (0, 0, -1):
        right, up = (1, 0, 0), (0, 1, 0)
    return right, up


def collect(parts, alpha_map=None):
    out = []
    for name, part in parts:
        a = (alpha_map or {}).get(name, 1.0)
        for m, col, lab in part.items:
            for fc in m.f:
                out.append(([m.v[i] for i in fc], col, a))
    return out


def draw(ax, faces, fwd, light=norm((-0.4, 0.5, 0.8)), edge=False):
    right, up = view_basis(fwd)
    polys, cols, depth = [], [], []
    for pts, col, a in faces:
        e1 = [pts[1][i] - pts[0][i] for i in range(3)]
        e2 = [pts[2][i] - pts[0][i] for i in range(3)]
        n = cross(e1, e2)
        if dot(n, n) < 1e-12 and len(pts) == 4:
            e2 = [pts[3][i] - pts[0][i] for i in range(3)]
            n = cross(e1, e2)
        n = norm(n)
        if dot(n, fwd) > 0.02 and a >= 1.0:     # 후면 컬링
            continue
        sh = 0.45 + 0.55 * abs(dot(n, light))
        c = tuple(min(1, col[i] / 255.0 * sh) for i in range(3)) + (a,)
        polys.append([(dot(p, right), dot(p, up)) for p in pts])
        cols.append(c)
        depth.append(sum(dot(p, fwd) for p in pts) / len(pts))
    order = sorted(range(len(polys)), key=lambda i: -depth[i])
    pc = PolyCollection([polys[i] for i in order], facecolors=[cols[i] for i in order],
                        edgecolors=[cols[i] for i in order] if not edge else "k", linewidths=0.15)
    ax.add_collection(pc)
    ax.set_aspect("equal")
    ax.autoscale_view()
    return right, up


def dim_h(ax, x0, x1, y, text, off=0, color="#c0392b"):
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", color=color, lw=0.8))
    ax.text((x0 + x1) / 2, y + 8 + off, text, ha="center", va="bottom", fontsize=7, color=color)


def dim_v(ax, x, y0, y1, text, color="#c0392b", ha="left"):
    ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", color=color, lw=0.8))
    ax.text(x + (6 if ha == "left" else -6), (y0 + y1) / 2, text, ha=ha, va="center", fontsize=7, color=color,
            rotation=90)


MAIN = [(n, P[n]) for n in W.PART_ORDER]
CHAIR = [(n, P[n]) for n in W.PART_ORDER if n != "Human Reference"]


def finish(ax, title, pad=80):
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad)
    ax.set_title(title, fontsize=10)
    ax.grid(True, lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=6)


def render_views():
    files = []
    v = d.v
    # 정면
    for nm, fwd, with_h in (("front", VIEWS["front"], False), ("side", VIEWS["side"], False),
                            ("top", VIEWS["top"], False), ("persp", VIEWS["persp"], False),
                            ("persp_human", VIEWS["persp"], True)):
        fig, ax = plt.subplots(figsize=(8, 8), dpi=160)
        faces = collect(MAIN if with_h else CHAIR, {"Human Reference": 0.85})
        draw(ax, faces, fwd)
        if nm == "side":
            ax.axhline(0, color="k", lw=0.8)
            dim_h(ax, 0, v["wheelbase"], -40, "휠베이스 %d" % v["wheelbase"])
            dim_h(ax, v["seat_rear_x"], v["seat_front_x"], v["seat_front_h"] + 40, "좌석깊이 %d" % v["seat_depth"])
            dim_v(ax, v["seat_front_x"] + 20, 0, v["seat_front_h"], "좌석전면 %d" % v["seat_front_h"])
            dim_v(ax, v["seat_rear_x"] + 160, v["seat_rear_h"], v["armrest_top_abs"],
                  "팔걸이 +%d" % v["armrest_h_above_seat"])
            front = v["plate_heel_x"] + v["plate_len"]
            dim_h(ax, -R_REAR, front, -90, "전장(수납) %d" % v["overall_length_stowed"])
            dim_v(ax, v["plate_heel_x"] + v["plate_len"] + 20, 0, v["plate_top_h"], "발판 %d" % v["plate_top_h"])
            ax.set_xlabel("X (mm, 전방 →)", fontsize=7); ax.set_ylabel("Z (mm)", fontsize=7)
        if nm == "front":
            ax.axhline(0, color="k", lw=0.8)
            dim_h(ax, -v["overall_width"] / 2, v["overall_width"] / 2, -40, "전폭 %d" % v["overall_width"])
            dim_h(ax, -v["seat_width"] / 2, v["seat_width"] / 2, v["seat_front_h"] + 60,
                  "좌석폭 %d" % v["seat_width"])
            dim_h(ax, -v["armrest_inner_gap"] / 2, v["armrest_inner_gap"] / 2, v["armrest_top_abs"] + 30,
                  "팔걸이 안쪽 %d" % v["armrest_inner_gap"])
            ax.set_xlabel("Y (mm, 사용자 왼쪽 →)", fontsize=7)
        if nm == "top":
            ax.add_patch(plt.Circle((v["caster_swivel_x"], v["y_c"]), v["caster_swivel_envelope_r"],
                                    fill=False, ls="--", color="#c0392b", lw=0.7))
            ax.add_patch(plt.Circle((v["caster_swivel_x"], -v["y_c"]), v["caster_swivel_envelope_r"],
                                    fill=False, ls="--", color="#c0392b", lw=0.7))
            ax.text(v["caster_swivel_x"], v["y_c"] + 160, "캐스터 회전궤적", fontsize=6, color="#c0392b", ha="center")
            ax.set_xlabel("X (mm)", fontsize=7); ax.set_ylabel("Y (mm)", fontsize=7)
        titles = {"front": "정면도 (Front)", "side": "측면도 (Right side)", "top": "평면도 (Top)",
                  "persp": "사시도 (Perspective, 등각 투영)", "persp_human": "사시도 + 170cm 파라메트릭 더미"}
        finish(ax, titles[nm])
        if nm in ("persp", "persp_human"):
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        p = os.path.join(OUT, "views_%s.png" % nm)
        fig.savefig(p, bbox_inches="tight"); plt.close(fig)
        files.append(p)
    return files


R_REAR = W.R("rear_D") / 2.0


def seat_review():
    v = d.v
    files = []
    side = VIEWS["side"]
    # G1 착석 검토 (측면)
    fig, ax = plt.subplots(figsize=(10, 9), dpi=160)
    draw(ax, collect(CHAIR), side)
    draw(ax, collect([("Human Reference", P["Human Reference"])], {"Human Reference": 0.55}), side)
    ax.axhline(0, color="k", lw=0.8)
    pts = W.reference_points(d)
    for k in ("Hip joint", "Knee joint", "Ankle joint", "Lumbar center", "Headrest center", "Seat front (compressed)"):
        x, _, z = pts[k]
        ax.plot([x], [z], "o", ms=3, color="#c0392b")
        ax.text(x + 10, z + 10, k, fontsize=6, color="#c0392b")
    sf = (v["seat_front_x"], v["seat_front_h"])
    pop = v["seat_rear_x"] + W.A("앉은엉덩이오금수평길이")
    dim_h(ax, sf[0], pop, sf[1] - 60, "무릎 뒤 여유 %d (P5 %d)" % (v["knee_clear_P50"], v["knee_clear_P5"]))
    elbow_z = v["seat_rear_h"] + W.A("앉은팔꿈치높이")
    ax.plot([v["seat_rear_x"] + 40, v["seat_rear_x"] + 300], [elbow_z, elbow_z], ":", color="#2c3e50", lw=0.8)
    ax.text(v["seat_rear_x"] + 305, elbow_z, "앉은팔꿈치높이 → 팔걸이 +%d" % W.R("elbow_rest_offset"),
            fontsize=6, va="center")
    dim_v(ax, sf[0] + 30, v["plate_top_h"], sf[1], "좌면↔발판 %d" % (sf[1] - v["plate_top_h"]))
    ax.text(pts["Knee joint"][0] + 30, pts["Knee joint"][2] + 60,
            "무릎 내각 %.0f° / 정강이 전경 %.0f°" % (v["knee_angle_seated"], v["shank_incline_deg"]), fontsize=7)
    finish(ax, "G-1 착석 검토 (측면) — 파라메트릭 더미, 사이즈코리아 3D 착석 스캔 아님")
    p = os.path.join(OUT, "seating_side_review.png"); fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    files.append(p)

    # G2 재활 자세 (슬라이딩 / 페달)
    for key, title in (("Rehab Pose - Slide end", "G-2 슬라이딩식: 기본자세 → 신전 끝(레일 %s°, 스트로크 %s mm)"),
                       ("Rehab Pose - Pedal", "G-3 회전 페달식: 크랭크 중심·궤적 및 0°/180° 다리 자세")):
        if key not in EXTRA:
            continue
        fig, ax = plt.subplots(figsize=(10, 8), dpi=160)
        draw(ax, collect(CHAIR), side)
        draw(ax, collect([("Human Reference", P["Human Reference"])], {"Human Reference": 0.35}), side)
        draw(ax, collect([(key, EXTRA[key])], {key: 0.6}), side)
        ax.axhline(0, color="k", lw=0.8)
        if key.endswith("Slide end"):
            s = v["slide"]; tt = title % (s["angle"], s["stroke"])
            a0 = v["ankle"]; a1 = s["end_ankle"]
            ax.annotate("", a1, a0, arrowprops=dict(arrowstyle="->", color="#2c6fbb", lw=1.2))
            ax.text(a1[0] + 10, a1[1], "무릎 %.0f°" % s["knee"], fontsize=7, color="#2c6fbb")
        else:
            pe = v["pedal"]; tt = title
            ax.text(pe["cx"] + pe["r"] + 15, pe["cz"], "무릎 %.0f°~%.0f°" % (pe["kmin"], pe["kmax"]), fontsize=7,
                    color="#d35400")
        finish(ax, tt)
        p = os.path.join(OUT, "seating_%s.png" % ("slide" if "Slide" in key else "pedal"))
        fig.savefig(p, bbox_inches="tight"); plt.close(fig)
        files.append(p)

    # G4 정면 착석
    fig, ax = plt.subplots(figsize=(8, 8), dpi=160)
    draw(ax, collect(MAIN, {"Human Reference": 0.8}), VIEWS["front"])
    ax.axhline(0, color="k", lw=0.8)
    finish(ax, "G-4 착석 정면 — 어깨·엉덩이 폭 vs 등받이·좌석·팔걸이")
    p = os.path.join(OUT, "seating_front_review.png"); fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    files.append(p)
    return files


def write_tables():
    with open(os.path.join(OUT, "dims.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["group", "key", "value", "unit", "tag", "formula/basis"])
        for r in d.rows:
            w.writerow(r)
    with open(os.path.join(OUT, "anthropometry_inputs.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["사이즈코리아 항목명", "value_mm", "tag", "note"])
        for k, (val, tag, note) in W.ANTHRO.items():
            w.writerow([k, val, tag, note])
    with open(os.path.join(OUT, "parts_bbox.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["part", "xmin", "ymin", "zmin", "xmax", "ymax", "zmax", "L(X)", "W(Y)", "H(Z)"])
        for n in W.PART_ORDER:
            lo, hi = P[n].bbox()
            w.writerow([n] + ["%.1f" % x for x in lo + hi] + ["%.1f" % (hi[i] - lo[i]) for i in range(3)])
    res = W.checks(d, P)
    with open(os.path.join(OUT, "checks.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["type", "item", "result", "judgement"])
        for r in res:
            w.writerow(r)
    return res


if __name__ == "__main__":
    print(export_3dm(os.path.join(OUT, "RehabWheelchair_170cm_1to1.3dm")))
    res = write_tables()
    for r in res:
        print(" | ".join(r))
    for p in render_views() + seat_review():
        print(p)
