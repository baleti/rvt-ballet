using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\");
var log = new StringBuilder(); var eh = new StringBuilder();
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  int n = 0;
  foreach (Element e in new FilteredElementCollector(d).WherePasses(new LogicalOrFilter(new ElementIsElementTypeFilter(false), new ElementIsElementTypeFilter(true)))) {
    string cid = "none", cn = "";
    try { var c = e.Category; if (c != null) { cid = c.Id.ToString(); cn = c.Name; var pc = c.Parent; if (pc != null) cn = pc.Name + ":" + cn; } } catch (Exception) { cid = "err"; }
    eh.AppendLine("CAT " + e.Id.ToString() + " " + e.GetType().Name + " " + cid + " " + cn.Replace(" ", "_")); n++;
  }
  if ("__ENUM__" == "1") foreach (var v in Enum.GetValues(typeof(BuiltInCategory))) eh.AppendLine("BIC " + ((int)v).ToString() + " " + v.ToString());
  d.Close(false);
  System.IO.Directory.CreateDirectory(@"C:\wl\out"); System.IO.File.WriteAllText(@"C:\wl\out\__OUTNAME__.txt", eh.ToString());
  log.AppendLine("COUNT " + n);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
