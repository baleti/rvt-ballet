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
  log.AppendLine("RB count=" + new FilteredElementCollector(d).WhereElementIsNotElementType().GetElementCount() + " types=" + new FilteredElementCollector(d).WhereElementIsElementType().GetElementCount());
  foreach (var s in ids) {
    var e = d.GetElement(new ElementId(long.Parse(s)));
    if (e == null) { log.AppendLine("RB " + s + " missing"); continue; }
    var lp = e.Location as LocationPoint; var lc = e.Location as LocationCurve;
    string loc = lp != null ? lp.Point.X.ToString("F6") + " " + lp.Point.Y.ToString("F6") + " " + lp.Point.Z.ToString("F6") : (lc != null ? lc.Curve.GetEndPoint(0).X.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Y.ToString("F6") + " " + lc.Curve.GetEndPoint(0).Z.ToString("F6") : "noloc");
    var mark = e.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
    var grp = e.GroupId != ElementId.InvalidElementId ? d.GetElement(e.GroupId) as Group : null;
    if (grp != null) {
      var gt = grp.GroupType; var mem = grp.GetMemberIds().ToList(); int idx = mem.FindIndex(x => x.ToString() == s);
      log.AppendLine("GROUP " + s + " type=" + gt.Name + " members=" + mem.Count + " index=" + idx + " instances=" + gt.Groups.Size);
      foreach (Group gi in gt.Groups) {
        var mi = gi.GetMemberIds().ToList(); var gl = gi.Location as LocationPoint; var me = idx >= 0 && idx < mi.Count ? d.GetElement(mi[idx]) : null; var ml = me != null ? me.Location as LocationPoint : null;
        if (gl != null && ml != null) log.AppendLine("GI " + gi.Id + " rel=" + (ml.Point.X - gl.Point.X).ToString("F6") + " " + (ml.Point.Y - gl.Point.Y).ToString("F6") + " " + (ml.Point.Z - gl.Point.Z).ToString("F6"));
        else log.AppendLine("GI " + gi.Id + " members=" + mi.Count + " noloc");
      }
    }
    var fi = e as FamilyInstance;
    if (fi != null && fi.Host != null) {
      var hl = fi.Host.Location as LocationCurve; var pl = e.Location as LocationPoint; string dist = "n/a"; string width = "";
      if (hl != null && pl != null) { var c2 = hl.Curve; var pt = new XYZ(pl.Point.X, pl.Point.Y, c2.GetEndPoint(0).Z); var pr = c2.Project(pt); dist = pr != null ? pr.Distance.ToString("F6") : "noproj"; }
      var w = fi.Host as Wall; if (w != null) width = " wallwidth=" + w.Width.ToString("F6");
      log.AppendLine("HOST " + s + " host=" + fi.Host.Id + " " + fi.Host.GetType().Name + " dist_to_hostline=" + dist + width + " hostparam=" + (e.get_Parameter(BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM) != null ? e.get_Parameter(BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM).AsValueString() : "-"));
    }
    foreach (var tg in new FilteredElementCollector(d).OfClass(typeof(IndependentTag)).Cast<IndependentTag>()) {
      bool hit = false; try { hit = tg.GetTaggedLocalElementIds().Any(x => x.ToString() == s); } catch {}
      if (hit) { string head = "?"; try { var hp = tg.TagHeadPosition; head = hp.X.ToString("F6") + " " + hp.Y.ToString("F6") + " " + hp.Z.ToString("F6"); } catch {} log.AppendLine("TAG " + s + " tag=" + tg.Id + " head=" + head + " leader=" + tg.HasLeader); }
    }
    foreach (var dm in new FilteredElementCollector(d).OfClass(typeof(Dimension)).Cast<Dimension>()) {
      bool hit = false; try { foreach (Reference rf in dm.References) { if (rf.ElementId.ToString() == s) { hit = true; break; } } } catch {}
      if (hit) log.AppendLine("DIM " + s + " dim=" + dm.Id + " value=" + (dm.Value.HasValue ? dm.Value.Value.ToString("F6") : "-"));
    }
    log.AppendLine("RB " + s + " loc=" + loc + " group=" + e.GroupId + " mark=" + (mark != null ? mark.AsString() : "-"));
  }
  try { using (var t = new Transaction(d, "rg")) { t.Start(); d.Regenerate(); log.AppendLine("REGEN ok"); t.RollBack(); } } catch (Exception ex) { log.AppendLine("REGEN " + ex.GetType().Name + " " + ex.Message.Replace("\r", " ").Replace("\n", " ")); }
  d.Close(false);
  log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + " " + ex.Message); }
Console.WriteLine(log.ToString());
