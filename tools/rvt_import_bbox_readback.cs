using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\"); string[] ids = "__IDS__".Split(',');
var log = new StringBuilder();
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  foreach (var s in ids) {
    var e = d.GetElement(new ElementId(long.Parse(s)));
    if (e == null) { log.AppendLine("RB " + s + " missing"); continue; }
    var lp = e.Location as LocationPoint; var lc = e.Location as LocationCurve;
    string loc = lp != null ? lp.Point.X.ToString("F6") + " " + lp.Point.Y.ToString("F6") + " " + lp.Point.Z.ToString("F6") : (lc != null ? lc.Curve.GetEndPoint(0).X.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Y.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Z.ToString("F6") : "noloc");
    var bb = e.get_BoundingBox(null); if (bb != null) log.AppendLine("BB " + s + " min=" + bb.Min.X.ToString("F4") + "," + bb.Min.Y.ToString("F4") + "," + bb.Min.Z.ToString("F4") + " max=" + bb.Max.X.ToString("F4") + "," + bb.Max.Y.ToString("F4") + "," + bb.Max.Z.ToString("F4")); var li = e as RevitLinkInstance; string tfrot = null;
    if (lp == null && lc == null && li != null) { var t = li.GetTotalTransform(); loc = t.Origin.X.ToString("F6") + " " + t.Origin.Y.ToString("F6") + " " + t.Origin.Z.ToString("F6"); tfrot = (Math.Atan2(t.BasisX.Y, t.BasisX.X) * 180.0 / Math.PI).ToString("F4"); }
    var mark = e.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
    var fi2 = e as FamilyInstance; if (fi2 != null) { var tt = fi2.GetTransform(); log.AppendLine("TF " + s + " X=" + tt.BasisX.X.ToString("F4") + "," + tt.BasisX.Y.ToString("F4") + "," + tt.BasisX.Z.ToString("F4") + " Y=" + tt.BasisY.X.ToString("F4") + "," + tt.BasisY.Y.ToString("F4") + "," + tt.BasisY.Z.ToString("F4") + " Z=" + tt.BasisZ.X.ToString("F4") + "," + tt.BasisZ.Y.ToString("F4") + "," + tt.BasisZ.Z.ToString("F4") + " mirrored=" + fi2.Mirrored + " hand=" + fi2.HandFlipped + " facing=" + fi2.FacingOrientation.X.ToString("F4") + "," + fi2.FacingOrientation.Y.ToString("F4") + "," + fi2.FacingOrientation.Z.ToString("F4")); }
    string rot = lp != null ? (lp.Rotation * 180.0 / Math.PI).ToString("F4") : (tfrot ?? "-"); log.AppendLine("RB " + s + " loc=" + loc + " rotdeg=" + rot + " group=" + e.GroupId + " mark=" + (mark != null ? mark.AsString() : "-"));
  }
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
