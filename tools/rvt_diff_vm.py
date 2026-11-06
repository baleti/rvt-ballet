#!/usr/bin/env python3
"""rvt_diff_vm.py YEAR SAMPLE.rvt TAG OPSPEC [--no-fields]   paired experiment in the OFFLINE Revit VM (Autodesk samples / synthetic only).
OPSPEC (one string, ';' separates ops): move:ID:dx:dy:dz (feet) | rotate:ID:deg (about the instance origin, Z axis) | delete:ID[,ID..] | param:ID:BuiltInParameterName:value (double, internal units)
        | type:ID:TYPEID | none
Opens SAMPLE with audit, SaveAs BASE (no edit: Revit's own rewrite, the noise floor) and then applies the ops in one transaction and SaveAs AFTER.
Pulls both to work dir (default ~/c2x-diff/TAG/) and prints rvt_diff of  ORIG->BASE (what a plain Revit save changes),  BASE->AFTER (the edit pattern)  and  ORIG->AFTER.
Needs the VM lock (guest.vmlock); one VM instance at a time."""
import os, sys, re, json
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest, rvt_diff

def cs_for(ops, tag, file):
    body = []
    for o in [x for x in ops.split(';') if x and x != 'none']:
        p = o.split(':'); k = p[0]
        if k == 'move': body.append('{ var e = d.GetElement(new ElementId(%sL)); ElementTransformUtils.MoveElement(d, e.Id, new XYZ(%s, %s, %s)); log.AppendLine("OP move " + e.Id); }' % (p[1], p[2], p[3], p[4]))
        elif k == 'rotate': body.append('{ var e = d.GetElement(new ElementId(%sL)); var lp = (LocationPoint)e.Location; ElementTransformUtils.RotateElement(d, e.Id, Line.CreateBound(lp.Point, lp.Point + XYZ.BasisZ), %s * Math.PI / 180.0); log.AppendLine("OP rotate " + e.Id); }' % (p[1], p[2]))
        elif k == 'delete': body.append('{ var del = d.Delete(new List<ElementId>(new long[]{%s}.Select(x => new ElementId(x)))); log.AppendLine("OP delete cascade=" + string.Join(",", del.Select(x => x.ToString()))); }' % p[1])
        elif k == 'param': body.append('{ var e = d.GetElement(new ElementId(%sL)); var pr = e.get_Parameter(BuiltInParameter.%s); pr.Set(%s); log.AppendLine("OP param " + pr.Definition.Name); }' % (p[1], p[2], p[3]))
        elif k == 'type': body.append('{ var e = d.GetElement(new ElementId(%sL)); e.ChangeTypeId(new ElementId(%sL)); log.AppendLine("OP type"); }' % (p[1], p[2]))
        else: raise SystemExit('unknown op ' + o)
    return '''using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
using System.IO;
using System.Collections.Generic;
var app = UIApp.Application; var log = new StringBuilder();
EventHandler<Autodesk.Revit.DB.Events.FailuresProcessingEventArgs> fh = (s, e) => { foreach (var m in e.GetFailuresAccessor().GetFailureMessages()) log.AppendLine("FAILURE " + m.GetSeverity() + " " + m.GetDescriptionText()); };
app.FailuresProcessing += fh;
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(@"%(f)s"), op);
  Directory.CreateDirectory(@"C:\\wl\\out");
  var so = new SaveAsOptions(); so.OverwriteExistingFile = true;
  d.SaveAs(@"C:\\wl\\out\\%(t)s_base.rvt", so); log.AppendLine("SAVED base");
  using (var t = new Transaction(d, "rvtdiff")) { t.Start();
    %(b)s
    t.Commit(); }
  d.SaveAs(@"C:\\wl\\out\\%(t)s_after.rvt", so); log.AppendLine("SAVED after");
  d.Close(false);
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.Message.Replace("\\n", " ")); }
Console.WriteLine(log.ToString());
''' % {'f': file.replace('\\', '\\\\'), 't': tag, 'b': '\n    '.join(body)}

def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; year, src, tag, ops = int(a[0]), os.path.abspath(a[1]), a[2], a[3]
    wd = os.path.expanduser('~/c2x-diff/%s' % tag); os.makedirs(wd, exist_ok=True)
    rem = 'C:/wl/diff_%s_src.rvt' % tag
    with guest.vmlock():
        port = guest.fresh(year)
        if not port: raise SystemExit('no Revit port')
        try:
            guest.put(src, rem)
            out = guest.run_job(year, port, cs_for(ops, tag, rem), 'diff_' + tag, 900)
            print('\n'.join(l for l in out.replace('\r', '').splitlines() if l.startswith(('OP', 'SAVED', 'FAILURE', 'RESULT'))))
            ok = all(guest.get('C:/wl/out/%s_%s.rvt' % (tag, k), os.path.join(wd, '%s.rvt' % k)) for k in ('base', 'after'))
        finally: guest.down(year)
    if not ok or 'SAVED after' not in out: raise SystemExit('experiment failed:\n' + out[-1500:])
    nf = '--no-fields' in sys.argv
    for n, (x, y) in {'ORIG->BASE': (src, wd + '/base.rvt'), 'BASE->AFTER': (wd + '/base.rvt', wd + '/after.rvt'), 'ORIG->AFTER': (src, wd + '/after.rvt')}.items():
        rep = rvt_diff.diff(x, y, not nf); json.dump(rep, open(wd + '/' + n.replace('->', '_') + '.json', 'w'), indent=1, default=str)
        print('=====', n); print(rvt_diff.pretty(rep))

if __name__ == '__main__': main()
