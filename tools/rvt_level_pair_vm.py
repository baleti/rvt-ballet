import sys,os; sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
base=os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt'); out=os.path.expanduser('~/c3x-rvtread-work/pair2020')
cs=r'''using Autodesk.Revit.DB;
var app = UIApp.Application;
var d = app.OpenDocumentFile(@"C:\wl\lvp20_base.rvt");
d.SaveAs(@"C:\wl\out\lv_A.rvt", new SaveAsOptions { OverwriteExistingFile = true });
d.Close(false);
var d2 = app.OpenDocumentFile(@"C:\wl\out\lv_A.rvt");
using (var t = new Transaction(d2, "x")) { t.Start(); var lv = Level.Create(d2, 66.0); lv.Name = "Level added by API"; Console.WriteLine("new level id " + lv.Id); t.Commit(); }
d2.SaveAs(@"C:\wl\out\lv_B.rvt", new SaveAsOptions { OverwriteExistingFile = true });
d2.Close(false);
Console.WriteLine("saved");'''
with guest.vmlock():
    guest.put(base,'C:/wl/lvp20_base.rvt'); p=guest.fresh(2020)
    o=guest.run_job(2020,p,cs,'lvp20',2700); print(o[-600:])
    for n in 'AB': guest.get('C:/wl/out/lv_%s.rvt'%n,'%s/lv_%s.rvt'%(out,n),600)
    guest.down(2020)
