"""Revit-made witness: open a project, SaveAs A, move ONE wall +1 ft with ElementTransformUtils (hosted elements follow as Revit decides), SaveAs B. usage: rvt_wall_move_pair_vm.py YEAR SRC.rvt WALLID OUTDIR  (Autodesk samples only; offline VM)"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year, src, wid, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(out, exist_ok=True)
cs = r'''using Autodesk.Revit.DB;
var app = UIApp.Application;
var d = app.OpenDocumentFile(@"C:\wl\wmp_base.rvt");
d.SaveAs(@"C:\wl\out\wmp_A.rvt", new SaveAsOptions { OverwriteExistingFile = true });
d.Close(false);
var d2 = app.OpenDocumentFile(@"C:\wl\out\wmp_A.rvt");
using (var t = new Transaction(d2, "mv")) { t.Start(); ElementTransformUtils.MoveElement(d2, new ElementId((long)WID), new XYZ(1, 0, 0)); t.Commit(); }
d2.SaveAs(@"C:\wl\out\wmp_B.rvt", new SaveAsOptions { OverwriteExistingFile = true });
d2.Close(false);
Console.WriteLine("saved");'''.replace('WID', wid)
with guest.vmlock():
    guest.put(src, 'C:/wl/wmp_base.rvt'); p = guest.fresh(year)
    o = guest.run_job(year, p, cs, 'wmp%d' % year, 2700); print(o[-600:])
    for n in 'AB': guest.get('C:/wl/out/wmp_%s.rvt' % n, '%s/wmp_%s.rvt' % (out, n), 600)
    guest.down(year)
