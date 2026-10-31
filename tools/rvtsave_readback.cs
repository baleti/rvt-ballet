using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\"); string[] ids = "__IDS__".Split(',');
var log = new StringBuilder();
EventHandler<Autodesk.Revit.DB.Events.FailuresProcessingEventArgs> fh = (s, e) => { foreach (var m in e.GetFailuresAccessor().GetFailureMessages()) log.AppendLine("FAILURE " + m.GetSeverity() + " " + m.GetDescriptionText()); };
app.FailuresProcessing += fh;
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  foreach (var s in ids) {
    var e = d.GetElement(new ElementId(long.Parse(s)));
    if (e == null) { log.AppendLine("RB " + s + " missing"); continue; }
    var lp = e.Location as LocationPoint; var lc = e.Location as LocationCurve;
    string loc = lp != null ? lp.Point.X.ToString("F6") + " " + lp.Point.Y.ToString("F6") + " " + lp.Point.Z.ToString("F6") : (lc != null ? lc.Curve.GetEndPoint(0).X.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Y.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Z.ToString("F6") : "noloc");
    var mark = e.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
    log.AppendLine("RB " + s + " loc=" + loc + " group=" + e.GroupId + " mark=" + (mark != null ? mark.AsString() : "-"));
  }
  try { using (var t = new Transaction(d, "rg")) { t.Start(); d.Regenerate(); log.AppendLine("REGEN ok"); t.RollBack(); } } catch (Exception ex) { log.AppendLine("REGEN " + ex.GetType().Name + " " + ex.Message.Replace("\r", " ").Replace("\n", " ")); }
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
