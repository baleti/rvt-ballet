"""rvtsave_cascade.py YEAR IDS FILE: open FILE in the Revit VM, delete IDS through the Revit API in a rolled-back transaction, print the element count before/after and how many ids Revit deleted (cascade check for writer deletes)"""
import sys,os
sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab/campaign'))
import guest
year=int(sys.argv[1]); ids=sys.argv[2]; f=sys.argv[3]
CS=r'''using Autodesk.Revit.DB;
using System.Linq;
var app = UIApp.Application; var op = new OpenOptions(); op.Audit = true;
var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(@"__FILE__".Replace("/", "\\")), op);
Func<int> n = () => new FilteredElementCollector(d).WhereElementIsNotElementType().GetElementCount();
int b = n(); var ids = "__IDS__".Split(',').Select(x => new ElementId(long.Parse(x))).ToList();
using (var t = new Transaction(d, "x")) { t.Start(); var del = d.Delete(ids); Console.WriteLine("CASC before=" + b + " after=" + n() + " deleted_ids=" + del.Count); t.RollBack(); }
d.Close(false); Console.WriteLine("CASC done");'''
with guest.vmlock():
    port=guest.fresh(year); guest.put(f,'C:/wl/casc.rvt')
    out=guest.run_job(year,port,CS.replace('__FILE__','C:/wl/casc.rvt').replace('__IDS__',ids),'casc',300)
    print('\n'.join(l for l in out.replace('\r','').splitlines() if l.startswith('CASC') or 'rror' in l)[:800]); guest.down(year)
