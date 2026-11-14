using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\");
var log = new StringBuilder(); var o = new StringBuilder();
string T(string s) { return (s ?? "").Replace("\t", " ").Replace("\r", " ").Replace("\n", " "); }
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  int n = 0;
  foreach (Element e in new FilteredElementCollector(d).WherePasses(new LogicalOrFilter(new ElementIsElementTypeFilter(false), new ElementIsElementTypeFilter(true)))) {
    string cid = "none", cn = "", nm = "", tid = "-1", lid = "-1", ov = "-1";
    try { var c = e.Category; if (c != null) { cid = c.Id.ToString(); cn = c.Name; } } catch (Exception) { cid = "err"; }
    try { nm = e.Name; } catch (Exception) { nm = "<err>"; }
    try { tid = e.GetTypeId().ToString(); } catch (Exception) { }
    try { lid = e.LevelId.ToString(); } catch (Exception) { }
    try { ov = e.OwnerViewId.ToString(); } catch (Exception) { }
    o.AppendLine("E\t" + e.Id + "\t" + e.GetType().Name + "\t" + cid + "\t" + T(cn) + "\t" + T(nm) + "\t" + tid + "\t" + lid + "\t" + ov + "\t" + (e is ElementType ? 1 : 0)); n++;
    if (e is View v) {
      string gl = "-1"; try { if (v.GenLevel != null) gl = v.GenLevel.Id.ToString(); } catch (Exception) { }
      o.AppendLine("V\t" + e.Id + "\t" + v.ViewType + "\t" + (v.IsTemplate ? 1 : 0) + "\t" + gl + "\t" + T(v.Name));
    }
    if (e is ViewSheet s) {
      string idt = ""; try { var p = s.get_Parameter(BuiltInParameter.SHEET_ISSUE_DATE); if (p != null) idt = p.AsString(); } catch (Exception) { }
      string rv = ""; try { var p = s.get_Parameter(BuiltInParameter.SHEET_CURRENT_REVISION); if (p != null) rv = p.AsString(); } catch (Exception) { }
      string vps = ""; try { vps = string.Join(",", s.GetAllPlacedViews().Select(x => x.ToString())); } catch (Exception) { }
      o.AppendLine("S\t" + e.Id + "\t" + T(s.SheetNumber) + "\t" + T(s.Name) + "\t" + T(idt) + "\t" + T(rv) + "\t" + vps);
    }
    if (e is Wall w) { string wt = ""; try { wt = w.WallType.Name; } catch (Exception) { } o.AppendLine("W\t" + e.Id + "\t" + T(wt)); }
  }
  d.Close(false);
  System.IO.Directory.CreateDirectory(@"C:\wl\out"); System.IO.File.WriteAllText(@"C:\wl\out\__OUTNAME__.txt", o.ToString());
  log.AppendLine("COUNT " + n);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
