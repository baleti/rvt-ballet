#!/usr/bin/env python3
"""rvt_diff_vm.py YEAR SAMPLE.rvt TAG OPSPEC [--no-fields]   paired experiment in the OFFLINE Revit VM (Autodesk samples / synthetic only).
OPSPEC (one string, ';' separates ops): addwall:x0:y0:x1:y1:height (feet; type/level of first wall) | move:ID:dx:dy:dz (feet) | rotatefree:deg (first wall with no hosted family instances, about its midpoint) | rotate:ID:deg (about the instance origin, Z axis) | wallunjoin:WALLID (WallUtils.DisallowWallJoinAtEnd both ends) | wallend:WALLID:dlen (extend the end point along the wall by dlen ft, unjoined walls only) | elev:LEVELID:dz (Level.Elevation += dz, feet) | delete:ID[,ID..] | param:ID:BuiltInParameterName:value (double, internal units)
        | matcreate:NAME | tparamid:ID:NAME:ELEMID | tparamyn:ID (toggle first writable Yes/No param, logs its name) | tparamstr:ID:NAME:TEXT | tparam:ID:NAME:NUM (LookupParameter(NAME).Set, ID may be a type) | type:ID:TYPEID | duptype:TYPEID:NEWNAME (ElementType.Duplicate) | none
Opens SAMPLE with audit, SaveAs BASE (no edit: Revit's own rewrite, the noise floor) and then applies the ops in one transaction and SaveAs AFTER.
Pulls both to work dir (default ~/c2x-diff/TAG/) and prints rvt_diff of  ORIG->BASE (what a plain Revit save changes),  BASE->AFTER (the edit pattern)  and  ORIG->AFTER.
Needs the VM lock (guest.vmlock); one VM instance at a time."""
import os, sys, re, json
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest, rvt_diff

def EXT(f): return os.path.splitext(f)[1] or '.rvt'

def cs_for(ops, tag, file):
    body = []
    for o in [x for x in ops.split(';') if x and x != 'none']:
        p = o.split(':'); k = p[0]
        if k == 'move': body.append('{ var e = d.GetElement(new ElementId(%sL)); var bb0 = e.get_BoundingBox(null); ElementTransformUtils.MoveElement(d, e.Id, new XYZ(%s, %s, %s)); var bb1 = e.get_BoundingBox(null); log.AppendLine("OP move " + e.Id + " pinned=" + e.Pinned + " bbminx " + (bb0 != null ? bb0.Min.X.ToString("F6") : "null") + " -> " + (bb1 != null ? bb1.Min.X.ToString("F6") : "null")); }' % (p[1], p[2], p[3], p[4]))
        elif k == 'movefree': body.append('{ Wall w = null; foreach (Wall c in new FilteredElementCollector(d).OfClass(typeof(Wall)).Cast<Wall>()) { if (c.Location is LocationCurve && !c.GetDependentElements(new ElementClassFilter(typeof(FamilyInstance))).Any()) { w = c; break; } } if (w == null) throw new Exception("no unhosted wall"); ElementTransformUtils.MoveElement(d, w.Id, new XYZ(%s, %s, %s)); log.AppendLine("OP movefree wall " + w.Id); }' % (p[1], p[2], p[3]))
        elif k == 'rotatefree': body.append('{ Wall w = null; foreach (Wall c in new FilteredElementCollector(d).OfClass(typeof(Wall)).Cast<Wall>()) { if (c.Location is LocationCurve && !c.GetDependentElements(new ElementClassFilter(typeof(FamilyInstance))).Any()) { w = c; break; } } if (w == null) throw new Exception("no unhosted wall"); var lcr = (LocationCurve)w.Location; var cp2 = lcr.Curve.Evaluate(0.5, true); ElementTransformUtils.RotateElement(d, w.Id, Line.CreateBound(cp2, cp2 + XYZ.BasisZ), %s * Math.PI / 180.0); log.AppendLine("OP rotatefree wall " + w.Id); }' % p[1])
        elif k == 'rotate': body.append('{ var e = d.GetElement(new ElementId(%sL)); var lpt = e.Location as LocationPoint; XYZ cp = lpt != null ? lpt.Point : ((LocationCurve)e.Location).Curve.Evaluate(0.5, true); ElementTransformUtils.RotateElement(d, e.Id, Line.CreateBound(cp, cp + XYZ.BasisZ), %s * Math.PI / 180.0); log.AppendLine("OP rotate " + e.Id); }' % (p[1], p[2]))
        elif k == 'wallend': body.append('{ var e = d.GetElement(new ElementId(%sL)); var lc = (LocationCurve)e.Location; var c0 = lc.Curve; XYZ a0 = c0.GetEndPoint(0), b0 = c0.GetEndPoint(1); XYZ u = (b0 - a0).Normalize(); lc.Curve = Line.CreateBound(a0, b0 + u * %s); log.AppendLine("OP wallend " + e.Id + " len " + lc.Curve.Length); }' % (p[1], p[2]))
        elif k == 'addwall': body.append('{ Wall w0 = new FilteredElementCollector(d).OfClass(typeof(Wall)).Cast<Wall>().First(c => c.Location is LocationCurve); var ln = Line.CreateBound(new XYZ(%s, %s, 0), new XYZ(%s, %s, 0)); var nw = Wall.Create(d, ln, w0.WallType.Id, w0.LevelId, %s, 0.0, false, false); log.AppendLine("OP addwall " + nw.Id + " type " + w0.WallType.Id + " level " + w0.LevelId); }' % (p[1], p[2], p[3], p[4], p[5]))
        elif k == 'wallunjoin': body.append('{ var e = (Wall)d.GetElement(new ElementId(%sL)); WallUtils.DisallowWallJoinAtEnd(e, 0); WallUtils.DisallowWallJoinAtEnd(e, 1); log.AppendLine("OP wallunjoin " + e.Id); }' % p[1])
        elif k == 'elev': body.append('{ var lv = (Level)d.GetElement(new ElementId(%sL)); lv.Elevation = lv.Elevation + %s; log.AppendLine("OP elev " + lv.Elevation); }' % (p[1], p[2]))
        elif k == 'delete': body.append('{ var del = d.Delete(new List<ElementId>(new long[]{%s}.Select(x => new ElementId(x)))); log.AppendLine("OP delete cascade=" + string.Join(",", del.Select(x => x.ToString()))); }' % p[1])
        elif k == 'param': body.append('{ var e = d.GetElement(new ElementId(%sL)); var pr = e.get_Parameter(BuiltInParameter.%s); pr.Set(%s); log.AppendLine("OP param " + pr.Definition.Name); }' % (p[1], p[2], p[3]))
        elif k == 'tparam': body.append('{ var e = d.GetElement(new ElementId(%sL)); var pr = e.LookupParameter("%s"); if (pr == null) throw new Exception("no param"); if (%s) pr.Set((double)%s); else pr.Set((int)%s); log.AppendLine("OP tparam " + pr.Definition.Name + " = " + (pr.StorageType == StorageType.Double ? pr.AsDouble().ToString("R") : pr.AsInteger().ToString())); }' % (p[1], p[2], 'true', p[3], p[3]))
        elif k == 'tparamyn': body.append('{ var e = d.GetElement(new ElementId(%sL)); Parameter yn = null; foreach (Parameter c in e.Parameters) { if (c.IsReadOnly || c.StorageType != StorageType.Integer) continue; if (c.Definition.GetDataType() != SpecTypeId.Boolean.YesNo) continue; yn = c; break; } if (yn == null) throw new Exception("no yes/no param"); int before = yn.AsInteger(); yn.Set(before == 0 ? 1 : 0); log.AppendLine("OP tparamyn " + yn.Definition.Name + " " + before + " => " + yn.AsInteger()); }' % (p[1],))
        elif k == 'tparamstr': body.append('{ var e = d.GetElement(new ElementId(%sL)); var pr = e.LookupParameter("%s"); if (pr == null) throw new Exception("no param"); pr.Set("%s"); log.AppendLine("OP tparamstr " + pr.Definition.Name); }' % (p[1], p[2], p[3]))
        elif k == 'matcreate': body.append('{ var mid = Material.Create(d, "%s"); log.AppendLine("OP matcreate new id " + mid); }' % p[1])
        elif k == 'tparamid': body.append('{ var e = d.GetElement(new ElementId(%sL)); var pr = e.LookupParameter("%s"); if (pr == null) throw new Exception("no param"); pr.Set(new ElementId(%sL)); log.AppendLine("OP tparamid " + pr.Definition.Name + " = " + pr.AsElementId()); }' % (p[1], p[2], p[3]))
        elif k == 'type': body.append('{ var e = d.GetElement(new ElementId(%sL)); e.ChangeTypeId(new ElementId(%sL)); log.AppendLine("OP type"); }' % (p[1], p[2]))
        elif k == 'duptype': body.append('{ var e = (ElementType)d.GetElement(new ElementId(%sL)); var nt = e.Duplicate("%s"); log.AppendLine("OP duptype new id " + nt.Id); }' % (p[1], p[2]))
        else: raise SystemExit('unknown op ' + o)
    return '''using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
using System.IO;
using System.Collections.Generic;
var app = UIApp.Application; var log = new StringBuilder();
EventHandler<Autodesk.Revit.DB.Events.FailuresProcessingEventArgs> fh = (s, e) => { var fa = e.GetFailuresAccessor(); bool hasErr = false; foreach (var m in fa.GetFailureMessages()) { log.AppendLine("FAILURE " + m.GetSeverity() + " " + m.GetDescriptionText()); if (m.GetSeverity() == FailureSeverity.Warning) fa.DeleteWarning(m); else hasErr = true; } if (hasErr) e.SetProcessingResult(FailureProcessingResult.ProceedWithRollBack); };
app.FailuresProcessing += fh;
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(@"%(f)s"), op);
  Directory.CreateDirectory(@"C:\\wl\\out");
  var so = new SaveAsOptions(); so.OverwriteExistingFile = true;
  d.SaveAs(@"C:\\wl\\out\\%(t)s_base%(ext)s", so); log.AppendLine("SAVED base");
  using (var t = new Transaction(d, "rvtdiff")) { t.Start();
    %(b)s
    var cst = t.Commit(); log.AppendLine("OP commit " + cst); }
  d.SaveAs(@"C:\\wl\\out\\%(t)s_after%(ext)s", so); log.AppendLine("SAVED after");
  d.Close(false);
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.Message.Replace("\\n", " ")); }
Console.WriteLine(log.ToString());
''' % {'f': file.replace('\\', '\\\\'), 't': tag, 'ext': os.path.splitext(file)[1] or '.rvt', 'b': '\n    '.join(body)}

def one(year, port, src, tag, ops):
    rem = 'C:/wl/diff_%s_src%s' % (tag, os.path.splitext(src)[1] or '.rvt')
    guest.put(src, rem)
    out = guest.run_job(year, port, cs_for(ops, tag, rem), 'diff_' + tag, int(os.environ.get('RVTDIFF_TIMEOUT', '900')))
    print('[%s]' % tag, '\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('OP', 'SAVED', 'FAILURE', 'RESULT'))), flush=True)
    if not any(l.startswith(('OP', 'SAVED', 'FAILURE', 'RESULT')) for l in out.splitlines()): print('[%s] RAW guest output (no OP/SAVED/RESULT lines):' % tag, out[-1500:].replace('\r', ''), flush=True)
    wd = os.path.expanduser('~/c2x-diff/%s' % tag); os.makedirs(wd, exist_ok=True)
    ok = 'SAVED after' in out and all(guest.get('C:/wl/out/%s_%s%s' % (tag, k, EXT(src)), os.path.join(wd, '%s%s' % (k, EXT(src)))) for k in ('base', 'after'))
    return ok, wd

def report(src, wd, nf):
    for n, (x, y) in {'ORIG->BASE': (src, wd + '/base' + EXT(src)), 'BASE->AFTER': (wd + '/base' + EXT(src), wd + '/after' + EXT(src)), 'ORIG->AFTER': (src, wd + '/after' + EXT(src))}.items():
        rep = rvt_diff.diff(x, y, not nf); json.dump(rep, open(wd + '/' + n.replace('->', '_') + '.json', 'w'), indent=1, default=str)
        print('=====', wd, n); print(rvt_diff.pretty(rep), flush=True)

def main():
    """BATCH: rvt_diff_vm.py --batch FILE  (lines: YEAR SAMPLE TAG OPSPEC; one VM lock for the whole file, fresh Revit per line; diffs run after the VM is released)"""
    nf = '--no-fields' in sys.argv
    if '--batch' in sys.argv:
        jobs = [l.split(None, 3) for l in open(sys.argv[sys.argv.index('--batch') + 1]) if l.strip() and not l.startswith('#')]
        done = []
        with guest.vmlock():
            for y, src, tag, ops in jobs:
                y = int(y); src = os.path.abspath(os.path.expanduser(src)); port = guest.fresh(y)
                if not port: print('[%s] no Revit port' % tag); continue
                try: ok, wd = one(y, port, src, tag, ops.strip())
                finally: guest.down(y)
                if ok: done.append((src, wd))
                else: print('[%s] experiment failed' % tag)
        for src, wd in done: report(src, wd, nf)
        return
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; year, src, tag, ops = int(a[0]), os.path.abspath(a[1]), a[2], a[3]
    with guest.vmlock():
        port = guest.fresh(year)
        if not port: raise SystemExit('no Revit port')
        try: ok, wd = one(year, port, src, tag, ops)
        finally: guest.down(year)
    if not ok: raise SystemExit('experiment failed')
    report(src, wd, nf)

if __name__ == '__main__': main()
