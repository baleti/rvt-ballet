using Autodesk.Revit.DB;
using System.Linq;
using System;
using System.Collections.Generic;
using System.Text;
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\"); string[] items = "__IDS__".Split(',');
var log = new StringBuilder();
Func<byte[], IEnumerable<byte>> Sha = b => { var t = Type.GetType("System.Security.Cryptography.SHA256, System.Security.Cryptography") ?? Type.GetType("System.Security.Cryptography.SHA256"); var h = t.GetMethod("Create", Type.EmptyTypes).Invoke(null, null); return (byte[])h.GetType().GetMethod("ComputeHash", new[] { typeof(byte[]) }).Invoke(h, new object[] { b }); };
try {
  var op = new OpenOptions(); op.Audit = true;
  var d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), op);
  foreach (var it in items) {
    var parts = it.Split('|'); var e = d.GetElement(new ElementId(long.Parse(parts[0])));
    if (e == null) { log.AppendLine("RB " + it + " element missing"); continue; }
    if (parts[1] == "@symbol") { var fi = e as FamilyInstance; log.AppendLine("RB " + it + " symbol=" + (fi == null ? "none" : fi.Symbol.Id.ToString())); continue; }
    if (parts[1] == "@bbox") { var bb = e.get_BoundingBox(null); log.AppendLine("RB " + it + (bb == null ? " bbox=none" : " bbox=" + bb.Min.X.ToString("R") + "," + bb.Min.Y.ToString("R") + "," + bb.Min.Z.ToString("R") + "," + bb.Max.X.ToString("R") + "," + bb.Max.Y.ToString("R") + "," + bb.Max.Z.ToString("R"))); continue; }
    if (parts[1].StartsWith("*")) { foreach (Parameter q in e.Parameters) { if (q.Definition.Name.Contains(parts[1].Substring(1))) log.AppendLine("RB " + parts[0] + " param '" + q.Definition.Name + "' storage=" + q.StorageType + " value=" + (q.StorageType == StorageType.Integer ? q.AsInteger().ToString() : q.StorageType == StorageType.Double ? q.AsDouble().ToString("R") : q.AsValueString()) + " builtin=" + ((q.Definition as InternalDefinition) != null ? ((int)(q.Definition as InternalDefinition).BuiltInParameter).ToString() : "-")); } continue; }
    if (parts[1].StartsWith("#")) { var bp = e.get_Parameter((BuiltInParameter)int.Parse(parts[1].Substring(1))); log.AppendLine("RB " + it + (bp == null ? " builtin parameter missing" : " storage=" + bp.StorageType + " value=" + (bp.StorageType == StorageType.Integer ? bp.AsInteger().ToString() : bp.AsValueString()))); continue; }
    var p = e.LookupParameter(parts[1]);
    if (p == null) { log.AppendLine("RB " + it + " parameter missing"); continue; }
    string v = p.StorageType == StorageType.Double ? p.AsDouble().ToString("R") : p.StorageType == StorageType.Integer ? p.AsInteger().ToString() : p.StorageType == StorageType.String ? "(string, see utf16)" : p.AsValueString();
    string sv = p.StorageType == StorageType.String ? (p.AsString() ?? "") : null; string cps = sv != null ? " len=" + sv.Length + " utf16=" + (sv.Length > 200 ? ("LONG allx=" + sv.All(ch => ch == (char)120) + " sha=" + string.Join("", Sha((Encoding.Unicode.GetBytes(sv))).Select(x => x.ToString("x2")))) : string.Join(",", sv.Select(ch => ((int)ch).ToString("X")))) : ""; log.AppendLine("RB " + it + " storage=" + p.StorageType + " value=" + v + " shown=" + (p.StorageType == StorageType.String ? "-" : p.AsValueString()) + cps);
  }
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
