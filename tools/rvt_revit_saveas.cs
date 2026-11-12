using Autodesk.Revit.DB;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\"); string outp = @"__OUT__".Replace("/", "\\");
var log = new StringBuilder();
try {
  var op = new OpenOptions(); op.Audit = false;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  var so = new SaveAsOptions(); so.OverwriteExistingFile = true; so.Compact = false;
  d.SaveAs(outp, so);
  d.Close(false);
  log.AppendLine("RESULT ok saved " + outp);
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
