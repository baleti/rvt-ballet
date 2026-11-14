using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Visual;
using System.Linq;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\");
var log = new StringBuilder(); var o = new StringBuilder();
string C(Color c) { try { return (c == null || !c.IsValid) ? "-" : c.Red + "," + c.Green + "," + c.Blue; } catch (Exception) { return "-"; } }
void Walk(Asset a, string path, int depth, StringBuilder sb) {
  if (a == null || depth > 6) return;
  for (int i = 0; i < a.Size; i++) {
    AssetProperty p = a.Get(i); string nm = path + "/" + p.Name;
    try {
      if (p is AssetPropertyDoubleArray4d d4) { var v = d4.GetValueAsDoubles(); sb.Append(" " + nm.Replace(" ", "_") + "=" + string.Join(",", v.Select(x => x.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture)))); }
      else if (p is AssetPropertyDoubleArray3d d3) { var v = d3.GetValueAsXYZ(); sb.Append(" " + nm.Replace(" ", "_") + "=" + v.X.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture) + "," + v.Y.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture) + "," + v.Z.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture)); }
    } catch (Exception) { }
    try { foreach (var cp in p.GetAllConnectedProperties()) if (cp is Asset ca) Walk(ca, nm, depth + 1, sb); } catch (Exception) { }
  }
}
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  int nw = 0, nm = 0;
  foreach (Wall w in new FilteredElementCollector(d).OfClass(typeof(Wall)).Cast<Wall>()) {
    double h = -1; try { var p = w.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM); if (p != null) h = p.AsDouble(); } catch (Exception) { }
    string kind = ""; try { kind = w.WallType.Kind.ToString(); } catch (Exception) { }
    o.AppendLine("W\t" + w.Id + "\t" + w.GetTypeId() + "\t" + h.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + "\t" + kind); nw++;
  }
  foreach (WallType t in new FilteredElementCollector(d).OfClass(typeof(WallType)).Cast<WallType>()) {
    string mats = ""; try { var cs = t.GetCompoundStructure(); if (cs != null) mats = string.Join(",", cs.GetLayers().Select(L => L.MaterialId.ToString())); } catch (Exception) { }
    o.AppendLine("T\t" + t.Id + "\t" + t.Kind + "\t" + mats);
  }
  foreach (Material m in new FilteredElementCollector(d).OfClass(typeof(Material)).Cast<Material>()) {
    var sb = new StringBuilder();
    sb.Append("M\t" + m.Id + "\tcolor=" + C(m.Color));
    try { sb.Append(" cutfg=" + C(m.CutForegroundPatternColor) + " cutbg=" + C(m.CutBackgroundPatternColor) + " surffg=" + C(m.SurfaceForegroundPatternColor) + " surfbg=" + C(m.SurfaceBackgroundPatternColor)); } catch (Exception) { }
    sb.Append(" asset=" + m.AppearanceAssetId);
    try { var ae = d.GetElement(m.AppearanceAssetId) as AppearanceAssetElement; if (ae != null) Walk(ae.GetRenderingAsset(), "app", 0, sb); } catch (Exception ex) { sb.Append(" asseterr=" + ex.GetType().Name); }
    o.AppendLine(sb.ToString()); nm++;
  }
  d.Close(false);
  System.IO.Directory.CreateDirectory(@"C:\wl\out"); System.IO.File.WriteAllText(@"C:\wl\out\__OUTNAME__.txt", o.ToString());
  log.AppendLine("COUNT walls " + nw + " materials " + nm);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
