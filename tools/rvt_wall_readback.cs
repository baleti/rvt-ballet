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
    var w = d.GetElement(new ElementId(long.Parse(s))) as Wall;
    if (w == null) { log.AppendLine("RB " + s + " missing"); continue; }
    var c0 = (w.Location as LocationCurve).Curve;
    log.AppendLine("RB " + s + " p0=" + c0.GetEndPoint(0).ToString() + " p1=" + c0.GetEndPoint(1).ToString() + " type=" + w.WallType.Name + " typeid=" + w.GetTypeId() + " level=" + w.LevelId + " h=" + w.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble().ToString("F4"));
  }
  var all = new FilteredElementCollector(d).WhereElementIsNotElementType().ToElementIds().Count;
  var ws = new FilteredElementCollector(d).OfClass(typeof(Wall)).Cast<Wall>().ToList();
  long h = 17; foreach (var w in ws.OrderBy(x => x.Id.Value)) { var cc = (w.Location as LocationCurve); if (cc == null) continue; h = h * 31 + (long)(cc.Curve.GetEndPoint(0).X * 1000) + (long)(cc.Curve.GetEndPoint(1).Y * 1000) + w.Id.Value; }
  log.AppendLine("WL elements=" + all + " walls=" + ws.Count + " hash=" + h);
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
