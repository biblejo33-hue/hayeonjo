#! python 2
# -*- coding: utf-8 -*-
"""
링(파이프) 단면 지름만 키우는 스크립트 - 중심선(링 크기)은 그대로 유지.
사용법: Rhino 명령창 -> RunPythonScript (Rhino 8은 ScriptEditor 에서 열고 실행)
 1) 변형할 물체 선택 (기본: '기본값' 레이어의 보이는 물체 전부)
 2) 목표 지름 입력 (현재 35mm 기준, 기본 50)
위쪽 Ø28 튜브도 같은 비율로 커짐 (50 입력 시 28 -> 40).
"""
import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

CENTERLINE_ID = "9d380a07-f30e-4098-adc4-624bb823e6b4"   # CURVE 레이어의 닫힌 중심선
CURRENT_D = 35.0


class PipeMorph(Rhino.Geometry.SpaceMorph):
    def __init__(self, crv, k):
        self.crv = crv
        self.k = k

    def MorphPoint(self, p):
        ok, t = self.crv.ClosestPoint(p)
        c = self.crv.PointAt(t)
        return c + (p - c) * self.k


def main():
    cl_obj = sc.doc.Objects.FindId(System.Guid(CENTERLINE_ID))
    if cl_obj is None:
        cid = rs.GetObject("중심선(링 가운데 닫힌 커브)을 선택", rs.filter.curve)
        if not cid:
            return
        crv = rs.coercecurve(cid)
        skip = set([str(cid)])
    else:
        crv = cl_obj.Geometry
        skip = set([CENTERLINE_ID])

    target = rs.GetReal("목표 지름(mm)", 50.0, 1.0)
    if not target:
        return
    k = target / CURRENT_D

    ids = rs.GetObjects("변형할 물체 선택 (Enter = 기본값 레이어 전체)", preselect=True)
    if not ids:
        ids = [i for i in (rs.ObjectsByLayer("기본값") or []) if rs.IsObjectVisible(i)]
    ids = [i for i in ids if str(i) not in skip]

    morph = PipeMorph(crv, k)
    morph.PreserveStructure = False
    morph.Tolerance = sc.doc.ModelAbsoluteTolerance
    morph.QuickPreview = False

    rs.EnableRedraw(False)
    fail = 0
    for i in ids:
        g = rs.coercegeometry(i)
        if isinstance(g, Rhino.Geometry.Extrusion):
            g = g.ToBrep()
        else:
            g = g.Duplicate()
        if hasattr(g, "MakeDeformable"):
            g.MakeDeformable()
        if morph.Morph(g):
            sc.doc.Objects.Replace(System.Guid(str(i)), g)
        else:
            fail += 1
    rs.EnableRedraw(True)
    sc.doc.Views.Redraw()
    print("완료: %d개 변형, 실패 %d개, 배율 %.4f (35 -> %.1f mm)" % (len(ids) - fail, fail, k, target))


main()
