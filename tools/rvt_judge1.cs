using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using System.Linq;
using System.Text;
using System.Collections.Generic;
// rvt_judge1.cs (c4x-rvteditopus): ONE open of one file serves the whole Revit judgement that rvt_judge.py needed 3 tools and 4-6 Revit opens for.
// Same checks, same formulas: verify2.cs open (audit, FAILURE/DIALOG capture, curve dump, BBOXNULL, SaveAs + reopen + COMPARE),
// rvt_elemhash_readback.cs (EH hash of every element and type, identical string recipe), rvt_rotation_readback.cs (RB loc / TF lines),
// rvt_param_readback.cs (RB param lines). Everything goes to C:\wl\out\__TAG___j1.txt (the console transport truncates at ~10 KB).
var app = UIApp.Application;
string file = @"__FILE__".Replace("/", "\\"); string tag = "__TAG__";
var edIds = new HashSet<string>("__EDIDS__".Split(new[] { ',' }, System.StringSplitOptions.RemoveEmptyEntries));
string[] locIds = "__LOCIDS__".Split(new[] { ',' }, System.StringSplitOptions.RemoveEmptyEntries);
string twin = "__TWIN__";      // c8x-rvtjudge: Revit-made twin = apply the expected edit(s) through the API to this (unedited) file before hashing
string[] parItems = "__PARITEMS__".Split(new[] { (char)30 }, System.StringSplitOptions.RemoveEmptyEntries);
System.IO.Directory.CreateDirectory(@"C:\wl\out");
var log = new StringBuilder();
EventHandler<FailuresProcessingEventArgs> fh = (s, e) => { foreach (var m in e.GetFailuresAccessor().GetFailureMessages()) log.AppendLine("FAILURE " + m.GetSeverity() + " " + m.GetDescriptionText()); };
app.FailuresProcessing += fh;
EventHandler<Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs> dh = (s, e) => { log.AppendLine("DIALOG " + e.DialogId); };
try { UIApp.DialogBoxShowing += dh; } catch {}
Func<byte[], IEnumerable<byte>> Sha = b => { var t = Type.GetType("System.Security.Cryptography.SHA256, System.Security.Cryptography"); var h = t.GetMethod("Create", Type.EmptyTypes).Invoke(null, null); return (byte[])h.GetType().GetMethod("ComputeHash", new[] { typeof(byte[]) }).Invoke(h, new object[] { b }); };
Func<Document, string[]> dump = (d) => {
  var res = new List<string>();
  var all = new FilteredElementCollector(d).WhereElementIsNotElementType().ToList();
  foreach (var g in all.GroupBy(e => e.GetType().Name).OrderBy(g => g.Key)) res.Add("CLASS " + g.Key + " " + g.Count());
  res.Add("TOTAL " + all.Count);
  foreach (var c in all.OfType<CurveElement>()) { var cv = c.GeometryCurve; if (cv == null || !cv.IsBound) continue; var a = cv.GetEndPoint(0); var b = cv.GetEndPoint(1); res.Add("C " + c.Id + " " + c.GetType().Name + " " + a.X.ToString("F6") + " " + a.Y.ToString("F6") + " " + a.Z.ToString("F6") + " " + b.X.ToString("F6") + " " + b.Y.ToString("F6") + " " + b.Z.ToString("F6")); }
  foreach (var w in all.OfType<Wall>()) { var lc = w.Location as LocationCurve; if (lc == null) continue; var cv = lc.Curve; if (cv == null || !cv.IsBound) continue; var a = cv.GetEndPoint(0); var b = cv.GetEndPoint(1); var h = w.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM); res.Add("W " + w.Id + " " + a.X.ToString("F6") + " " + a.Y.ToString("F6") + " " + a.Z.ToString("F6") + " " + b.X.ToString("F6") + " " + b.Y.ToString("F6") + " " + b.Z.ToString("F6") + " h=" + (h != null ? h.AsDouble().ToString("F6") : "?") + " lvl=" + w.LevelId); }
  foreach (var l in all.OfType<Level>()) res.Add("L " + l.Id + " " + l.Name + " " + l.Elevation.ToString("F6"));
  foreach (var g in all.OfType<Grid>()) { var cv = g.Curve; if (cv == null || !cv.IsBound) continue; var a = cv.GetEndPoint(0); var b = cv.GetEndPoint(1); res.Add("G " + g.Id + " " + g.Name + " " + a.X.ToString("F6") + " " + a.Y.ToString("F6") + " " + b.X.ToString("F6") + " " + b.Y.ToString("F6")); }
  foreach (var t in all.OfType<TextNote>()) res.Add("T " + t.Id + " " + t.Text);
  foreach (var s in new FilteredElementCollector(d).WhereElementIsElementType().OfType<ElementType>()) res.Add("ET " + s.Id + " " + s.Name);
  return res.ToArray();
};
var outp = new StringBuilder();
string phase = "open"; Document d = null; string[] d1 = null, d2 = null; var sw = System.Diagnostics.Stopwatch.StartNew();
try {
  var oo = new OpenOptions(); oo.Audit = true;
  d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(file), oo);
  log.AppendLine("T_OPEN " + sw.ElapsedMilliseconds);
  if (twin.Length > 0) {
    phase = "twin";
    using (var tr = new Transaction(d, "twin")) { tr.Start();
      foreach (var it in twin.Split(new[] { (char)30 }, System.StringSplitOptions.RemoveEmptyEntries)) {
        var q = it.Split('|'); var e = d.GetElement(new ElementId((__IDT__)long.Parse(q[1])));
        if (e == null) throw new Exception("twin element missing " + q[1]);
        if (q[0] == "move") ElementTransformUtils.MoveElement(d, e.Id, new XYZ(double.Parse(q[2], System.Globalization.CultureInfo.InvariantCulture), double.Parse(q[3], System.Globalization.CultureInfo.InvariantCulture), double.Parse(q[4], System.Globalization.CultureInfo.InvariantCulture)));
        else if (q[0] == "rotate") { var lp0 = e.Location as LocationPoint; if (lp0 == null) throw new Exception("twin rotate needs LocationPoint"); ElementTransformUtils.RotateElement(d, e.Id, Line.CreateBound(lp0.Point, lp0.Point + XYZ.BasisZ), double.Parse(q[2], System.Globalization.CultureInfo.InvariantCulture) * Math.PI / 180.0); }
        else if (q[0] == "param") { var p0 = e.LookupParameter(q[2]); if (p0 == null || p0.IsReadOnly) throw new Exception("twin parameter unusable " + q[2]);
          bool okp = p0.StorageType == StorageType.Integer ? p0.Set(int.Parse(q[3])) : p0.StorageType == StorageType.Double ? p0.Set(double.Parse(q[3], System.Globalization.CultureInfo.InvariantCulture)) : p0.StorageType == StorageType.String ? p0.Set(q[3]) : false;
          if (!okp) throw new Exception("twin parameter set refused " + q[2]); }
        else throw new Exception("twin kind unsupported " + q[0]);
      }
      tr.Commit(); }
    log.AppendLine("TWIN applied");
  }
  phase = "dump1"; d1 = dump(d);
  int bbn = 0; foreach (var c in new FilteredElementCollector(d).OfClass(typeof(CurveElement)).Cast<CurveElement>()) { if (c.get_BoundingBox(null) == null) bbn++; }
  log.AppendLine("BBOXNULL " + bbn);
  phase = "elemhash"; int n = 0;
  foreach (Element e in new FilteredElementCollector(d).WherePasses(new LogicalOrFilter(new ElementIsElementTypeFilter(false), new ElementIsElementTypeFilter(true)))) {
    uint h = 2166136261;
    var sb = new StringBuilder(e.GetType().Name + "|" + e.Name + "|" + e.GroupId + "|");
    try { foreach (Parameter p in e.Parameters.Cast<Parameter>().OrderBy(q => q.Definition.Name).ThenBy(q => q.Id.ToString())) {
      if (p.Definition.Name == "File Path") continue;
      string v = p.StorageType == StorageType.Double ? p.AsDouble().ToString("R") : p.StorageType == StorageType.Integer ? p.AsInteger().ToString() : p.StorageType == StorageType.String ? (p.AsString() ?? "") : p.StorageType == StorageType.ElementId ? p.AsElementId().ToString() : "";
      sb.Append(p.Definition.Name).Append('=').Append(v).Append(';'); } } catch (Exception) { sb.Append("paramerr"); }
    var lp = e.Location as LocationPoint; var lc = e.Location as LocationCurve;
    if (lp != null) sb.Append("LP" + lp.Point.X.ToString("F6") + "," + lp.Point.Y.ToString("F6") + "," + lp.Point.Z.ToString("F6"));
    if (lc != null && lc.Curve != null && lc.Curve.IsBound) sb.Append("LC" + lc.Curve.GetEndPoint(0).X.ToString("F6") + "," + lc.Curve.GetEndPoint(0).Y.ToString("F6") + "," + lc.Curve.GetEndPoint(1).X.ToString("F6") + "," + lc.Curve.GetEndPoint(1).Y.ToString("F6"));
    try { var bb = e.get_BoundingBox(null); if (bb != null) sb.Append("BB" + bb.Min.X.ToString("F4") + "," + bb.Min.Y.ToString("F4") + "," + bb.Min.Z.ToString("F4") + "," + bb.Max.X.ToString("F4") + "," + bb.Max.Y.ToString("F4") + "," + bb.Max.Z.ToString("F4")); } catch (Exception) { sb.Append("BBerr"); }
    var gr = e as Grid; if (gr != null) { try { var gc = gr.Curve; if (gc != null && gc.IsBound) sb.Append("GR" + gc.GetEndPoint(0).X.ToString("F6") + "," + gc.GetEndPoint(0).Y.ToString("F6") + "," + gc.GetEndPoint(1).X.ToString("F6") + "," + gc.GetEndPoint(1).Y.ToString("F6")); } catch (Exception) { sb.Append("GRerr"); } }
    var tn = e as TextNote; if (tn != null) sb.Append("TN" + tn.Coord.X.ToString("F6") + "," + tn.Coord.Y.ToString("F6"));
    foreach (char c in sb.ToString()) { h ^= c; h *= 16777619; }
    outp.AppendLine("EH " + e.Id.ToString() + " " + h.ToString("x8")); n++;
    if (edIds.Contains(e.Id.ToString())) outp.AppendLine("ED " + e.Id.ToString() + " " + sb.ToString().Replace("\r", " ").Replace("\n", " "));
  }
  log.AppendLine("COUNT " + n);
  phase = "locreadback";
  foreach (var s in locIds) {
    var e = d.GetElement(new ElementId((__IDT__)long.Parse(s)));
    if (e == null) { outp.AppendLine("RB " + s + " missing"); continue; }
    var lp = e.Location as LocationPoint; var lc = e.Location as LocationCurve;
    string loc = lp != null ? lp.Point.X.ToString("F6") + " " + lp.Point.Y.ToString("F6") + " " + lp.Point.Z.ToString("F6") : (lc != null ? lc.Curve.GetEndPoint(0).X.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Y.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Z.ToString("F6") : "noloc");
    if (lp == null && lc == null) { try { var bbx = e.get_BoundingBox(null); if (bbx != null) loc = bbx.Min.X.ToString("F6") + " " + bbx.Min.Y.ToString("F6") + " " + bbx.Min.Z.ToString("F6"); } catch (Exception) { } }      // no Location (WallSweep, ...): bbox min stands in so a move can be read back
    var li = e as RevitLinkInstance; string tfrot = null;
    if (lp == null && lc == null && li != null) { var t = li.GetTotalTransform(); loc = t.Origin.X.ToString("F6") + " " + t.Origin.Y.ToString("F6") + " " + t.Origin.Z.ToString("F6"); tfrot = (Math.Atan2(t.BasisX.Y, t.BasisX.X) * 180.0 / Math.PI).ToString("F4"); }
    var mark = e.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
    var fi2 = e as FamilyInstance; if (fi2 != null) { var tt = fi2.GetTransform(); outp.AppendLine("TF " + s + " X=" + tt.BasisX.X.ToString("F4") + "," + tt.BasisX.Y.ToString("F4") + "," + tt.BasisX.Z.ToString("F4") + " Y=" + tt.BasisY.X.ToString("F4") + "," + tt.BasisY.Y.ToString("F4") + "," + tt.BasisY.Z.ToString("F4") + " Z=" + tt.BasisZ.X.ToString("F4") + "," + tt.BasisZ.Y.ToString("F4") + "," + tt.BasisZ.Z.ToString("F4") + " mirrored=" + fi2.Mirrored + " hand=" + fi2.HandFlipped + " facing=" + fi2.FacingOrientation.X.ToString("F4") + "," + fi2.FacingOrientation.Y.ToString("F4") + "," + fi2.FacingOrientation.Z.ToString("F4")); }
    string rot = lp != null ? (lp.Rotation * 180.0 / Math.PI).ToString("F4") : (tfrot ?? "-"); outp.AppendLine("RB " + s + " loc=" + loc + " rotdeg=" + rot + " group=" + e.GroupId + " mark=" + (mark != null ? mark.AsString() : "-"));
  }
  phase = "parreadback";
  foreach (var it in parItems) {
    var parts = it.Split('|'); var e = d.GetElement(new ElementId((__IDT__)long.Parse(parts[0])));
    if (e == null) { outp.AppendLine("RBP " + it + " element missing"); continue; }
    var p = e.LookupParameter(parts[1]);
    if (p == null) { outp.AppendLine("RBP " + it + " parameter missing"); continue; }
    string v = p.StorageType == StorageType.Double ? p.AsDouble().ToString("R") : p.StorageType == StorageType.Integer ? p.AsInteger().ToString() : p.StorageType == StorageType.String ? "(string, see utf16)" : p.AsValueString();
    string sv = p.StorageType == StorageType.String ? (p.AsString() ?? "") : null; string cps = sv != null ? " len=" + sv.Length + " utf16=" + (sv.Length > 200 ? ("LONG allx=" + sv.All(ch => ch == (char)120) + " sha=" + string.Join("", Sha((Encoding.Unicode.GetBytes(sv))).Select(x => x.ToString("x2")))) : string.Join(",", sv.Select(ch => ((int)ch).ToString("X")))) : "";
    outp.AppendLine("RBP " + it + " storage=" + p.StorageType + " value=" + v + " shown=" + (p.StorageType == StorageType.String ? "-" : p.AsValueString()) + cps);
  }
  phase = "saveas";
  string sp = @"C:\wl\out\" + tag + "_j1saved" + System.IO.Path.GetExtension(file);
  d.SaveAs(sp, new SaveAsOptions { OverwriteExistingFile = true });
  d.Close(false); d = null;
  phase = "reopen";
  d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(sp), new OpenOptions());
  phase = "dump2"; d2 = dump(d);
  d.Close(false); d = null;
  try { System.IO.File.Delete(sp); } catch {}
  var s1 = new HashSet<string>(d1); var s2 = new HashSet<string>(d2);
  log.AppendLine("COMPARE only_original=" + d1.Count(x => !s2.Contains(x)) + " only_resaved=" + d2.Count(x => !s1.Contains(x)));
  foreach (var x in d1.Where(x => !s2.Contains(x)).Take(5)) log.AppendLine("  ORIG " + x); foreach (var x in d2.Where(x => !s1.Contains(x)).Take(5)) log.AppendLine("  SAVED " + x);
  log.AppendLine("T_TOTAL " + sw.ElapsedMilliseconds);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail phase=" + phase + " " + ex.GetType().Name + ": " + ex.Message.Replace("\r", " ").Replace("\n", " ")); try { if (d != null) d.Close(false); } catch {} }
app.FailuresProcessing -= fh;
try { UIApp.DialogBoxShowing -= dh; } catch {}
System.IO.File.WriteAllText(@"C:\wl\out\" + tag + "_j1.txt", log.ToString() + outp.ToString());
Console.WriteLine(log.ToString());
