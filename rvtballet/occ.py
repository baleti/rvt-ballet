"""OpenCascade helpers (cadquery-ocp): solids from loops/boxes, booleans, tessellation to Mesh. Units: feet, same as geom.py."""
import numpy as np
from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf, gp_Ax3, gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common, BRepAlgoAPI_Fuse
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from .geom import Mesh

def _wire(pts):
    mk = BRepBuilderAPI_MakePolygon()
    for p in pts: mk.Add(gp_Pnt(*[float(x) for x in p]))
    mk.Close(); return mk.Wire()

def prism(loops_xy, z0, z1):
    """vertical prism of planar loops (outer first, then holes) between z0 and z1"""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    outer = np.asarray(loops_xy[0], float)
    mf = BRepBuilderAPI_MakeFace(_wire([(x, y, z0) for x, y in outer]))
    for h in loops_xy[1:]:
        w = _wire([(x, y, z0) for x, y in np.asarray(h, float)]); w.Reverse(); mf.Add(w)
    return BRepPrimAPI_MakePrism(mf.Face(), gp_Vec(0, 0, float(z1 - z0))).Shape()

def box_frame(origin, ux, uy, uz):
    """parallelepiped given by origin and three edge vectors (must be orthogonal)"""
    o = np.asarray(origin, float); ux = np.asarray(ux, float); uy = np.asarray(uy, float); uz = np.asarray(uz, float)
    dx, dy, dz = np.linalg.norm(ux), np.linalg.norm(uy), np.linalg.norm(uz)
    x = ux / dx; y = uy / dy; z = np.cross(x, y)
    if np.dot(z, uz) < 0: o = o + uz        # right-handed frame points the other way: start from the opposite end and extend back
    ax = gp_Ax3(gp_Pnt(*o.tolist()), gp_Dir(*z.tolist()), gp_Dir(*x.tolist()))
    t = gp_Trsf(); t.SetTransformation(ax)                      # maps local -> world after inversion
    t.Invert()
    b = BRepPrimAPI_MakeBox(float(dx), float(dy), float(dz)).Shape()
    return BRepBuilderAPI_Transform(b, t, True).Shape()

def halfspace_below(point, normal, size=1e4):
    """big solid on the side of the plane opposite to `normal` (i.e. points p with (p-point).normal <= 0)"""
    n = np.asarray(normal, float); n = n / np.linalg.norm(n)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0]); u = np.cross(n, a); u /= np.linalg.norm(u); v = np.cross(n, u)
    o = np.asarray(point, float) - u * size / 2 - v * size / 2 - n * size
    return box_frame(o, u * size, v * size, n * size)

def cut(a, b):
    op = BRepAlgoAPI_Cut(a, b); op.Build(); return op.Shape() if op.IsDone() else a
def common(a, b):
    op = BRepAlgoAPI_Common(a, b); op.Build(); return op.Shape() if op.IsDone() else a
def fuse(a, b):
    op = BRepAlgoAPI_Fuse(a, b); op.Build(); return op.Shape() if op.IsDone() else a

def bounds(s):
    bb = Bnd_Box(); BRepBndLib.Add_s(s, bb); a = bb.CornerMin(); b = bb.CornerMax(); return np.array([a.X(), a.Y(), a.Z()]), np.array([b.X(), b.Y(), b.Z()])

def volume(s):
    p = GProp_GProps(); BRepGProp.VolumeProperties_s(s, p); return p.Mass()

def to_mesh(shape, defl=0.05):
    """tessellate every face -> Mesh (outward-oriented triangles)"""
    BRepMesh_IncrementalMesh(shape, defl, False, 0.3, True)
    V = []; F = []; off = 0
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        face = TopoDS.Face(ex.Current()); loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation(); rev = face.Orientation() == TopAbs_REVERSED
            n = tri.NbNodes()
            for i in range(1, n + 1):
                p = tri.Node(i).Transformed(trsf); V.append((p.X(), p.Y(), p.Z()))
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get(); F.append((off + a - 1, off + (c if rev else b) - 1, off + (b if rev else c) - 1))
            off += n
        ex.Next()
    return Mesh(np.array(V), np.array(F, np.int32)) if F else Mesh()


def extrude_polygon(pts3d, vec):
    """planar closed polygon (3D points) swept along vec -> solid"""
    f = BRepBuilderAPI_MakeFace(_wire(pts3d)).Face()
    return BRepPrimAPI_MakePrism(f, gp_Vec(*[float(x) for x in vec])).Shape()
