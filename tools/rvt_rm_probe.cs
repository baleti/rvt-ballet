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
  string ps = @"
$sig = @'
using System; using System.Runtime.InteropServices;
public class RMX {
  [StructLayout(LayoutKind.Sequential)] public struct UP { public uint pid; public System.Runtime.InteropServices.ComTypes.FILETIME t; }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct PI { public UP Proc; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string App; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=64)] public string Svc; public int AppType; public uint Status; public uint TsSession; [MarshalAs(UnmanagedType.Bool)] public bool Restartable; }
  [DllImport(""rstrtmgr.dll"", CharSet=CharSet.Unicode)] public static extern int RmStartSession(out uint h, int f, System.Text.StringBuilder key);
  [DllImport(""rstrtmgr.dll"", CharSet=CharSet.Unicode)] public static extern int RmRegisterResources(uint h, uint nf, string[] files, uint na, IntPtr a, uint ns, IntPtr s);
  [DllImport(""rstrtmgr.dll"")] public static extern int RmGetList(uint h, out uint need, ref uint have, [In, Out] PI[] info, out uint reasons);
  [DllImport(""rstrtmgr.dll"")] public static extern int RmEndSession(uint h);
}
'@
Add-Type -TypeDefinition $sig
$h = 0; $k = New-Object System.Text.StringBuilder 33
$r = [RMX]::RmStartSession([ref]$h, 0, $k); 'start=' + $r
$r = [RMX]::RmRegisterResources($h, 1, @('" + file.Replace("'", "''") + @"'), 0, [IntPtr]::Zero, 0, [IntPtr]::Zero); 'register=' + $r
$need = 0; $have = 8; $reasons = 0; $info = New-Object 'RMX+PI[]' 8
$r = [RMX]::RmGetList($h, [ref]$need, [ref]$have, $info, [ref]$reasons); 'getlist=' + $r + ' need=' + $need + ' have=' + $have
for ($i = 0; $i -lt $have; $i++) { 'HOLDER ' + $info[$i].App + ' pid=' + $info[$i].Proc.pid }
[void][RMX]::RmEndSession($h)
";
  var psi = new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -EncodedCommand " + System.Convert.ToBase64String(Encoding.Unicode.GetBytes(ps)));
  psi.RedirectStandardOutput = true; psi.RedirectStandardError = true; psi.UseShellExecute = false; psi.CreateNoWindow = true;
  var pr = Process.Start(psi); string o = pr.StandardOutput.ReadToEnd() + pr.StandardError.ReadToEnd(); pr.WaitForExit(60000);
  foreach (var l in o.Replace("\r", "").Split('\n')) if (l.Trim().Length > 0) log.AppendLine("RM " + l.Trim());
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
