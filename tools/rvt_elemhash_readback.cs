using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\");
var log = new StringBuilder(); var eh = new StringBuilder(); var ed = new StringBuilder(); var wantIds = new System.Collections.Generic.HashSet<string>("__IDS__".Split(','));
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  int n = 0;
  foreach (Element e in new FilteredElementCollector(d).WherePasses(new LogicalOrFilter(new ElementIsElementTypeFilter(false), new ElementIsElementTypeFilter(true)))) {
    uint h = 2166136261;
    var sb = new StringBuilder(e.GetType().Name + "|" + e.Name + "|" + e.GroupId + "|");
    try { foreach (Parameter p in e.Parameters.Cast<Parameter>().OrderBy(q => q.Definition.Name).ThenBy(q => q.Id.ToString())) {
      if (p.Definition.Name == "File Path") continue;      // the guest copy name differs per file: harness artifact, not a model change
      string v = p.StorageType == StorageType.Double ? p.AsDouble().ToString("R") : p.StorageType == StorageType.Integer ? p.AsInteger().ToString() : p.StorageType == StorageType.String ? (p.AsString() ?? "") : p.StorageType == StorageType.ElementId ? p.AsElementId().ToString() : "";
      sb.Append(p.Definition.Name).Append('=').Append(v).Append(';'); } } catch (Exception) { sb.Append("paramerr"); }
    var lp = e.Location as LocationPoint; var lc = e.Location as LocationCurve;
    if (lp != null) sb.Append("LP" + lp.Point.X.ToString("F6") + "," + lp.Point.Y.ToString("F6") + "," + lp.Point.Z.ToString("F6"));
    if (lc != null) sb.Append("LC" + lc.Curve.GetEndPoint(0).X.ToString("F6") + "," + lc.Curve.GetEndPoint(0).Y.ToString("F6") + "," + lc.Curve.GetEndPoint(1).X.ToString("F6") + "," + lc.Curve.GetEndPoint(1).Y.ToString("F6"));
    var tn = e as TextNote; if (tn != null) sb.Append("TN" + tn.Coord.X.ToString("F6") + "," + tn.Coord.Y.ToString("F6"));
    if (wantIds.Contains(e.Id.ToString())) ed.AppendLine("ED " + e.Id.ToString() + " " + sb.ToString());
    foreach (char c in sb.ToString()) { h ^= c; h *= 16777619; }
    eh.AppendLine("EH " + e.Id.ToString() + " " + h.ToString("x8")); n++;
  }
  d.Close(false);
  System.IO.Directory.CreateDirectory(@"C:\wl\out"); System.IO.File.WriteAllText(@"C:\wl\out\__OUTNAME__.txt", eh.ToString()); System.IO.File.WriteAllText(@"C:\wl\out\__OUTNAME__.ed.txt", ed.ToString());
  log.AppendLine("COUNT " + n);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
