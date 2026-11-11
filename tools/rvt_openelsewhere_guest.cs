using Autodesk.Revit.DB;
using System.Linq;
using System.Text;
using System.Diagnostics;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\");
var log = new StringBuilder();
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  var psi = new ProcessStartInfo(@"C:\Users\User\AppData\Local\Programs\Python\Python313\python.exe", "C:\\wl\\oe_run.py \"" + file + "\"");
  psi.RedirectStandardOutput = true; psi.RedirectStandardError = true; psi.UseShellExecute = false; psi.CreateNoWindow = true;
  var pr = Process.Start(psi); string o = pr.StandardOutput.ReadToEnd() + pr.StandardError.ReadToEnd(); pr.WaitForExit(60000);
  foreach (var l in o.Replace("\r", "").Split('\n')) if (l.Trim().Length > 0) log.AppendLine("RM " + l.Trim());
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
