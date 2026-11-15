#!/usr/bin/env python3
"""rvt_save_pattern_vm.py YEAR FILE : measure HOW Revit writes a .rvt on SaveAs (new file, overwrite of the same path, Save of an open model).
Takes one lane through the normal FIFO guest.vmlock (waits its turn, never bypasses locks), copies FILE into the offline guest, runs
tools/rvt_save_timeline.ps1 in the background (20 ms polling of size / mtime / NTFS file id / side files), lets a Revit API job do the saves,
fetches the CSV, classifies it (tools/rvt_save_timeline_classify.py) and appends one summary row to ~/demo-state/rvt-save-pattern.tsv (no paths, no names).
Raw CSV stays local in ~/c3x-tmp/. Run detached: nohup python3 tools/rvt_save_pattern_vm.py 2024 FILE > ~/c3x-tmp/savepat.log 2>&1 &"""
import os, sys, time, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); os.environ['STAGEB'] = '1'
import guest
sys.path.insert(0, HERE); from rvt_save_timeline_classify import classify
import csv

JOB = r'''
using Autodesk.Revit.DB;
using System.Text;
var app = UIApp.Application; var log = new StringBuilder(); Document d = null;
try {
  System.IO.Directory.CreateDirectory(@"C:\wl\sp");
  d = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(@"C:\wl\sp\src.rvt"), new OpenOptions());
  System.Threading.Thread.Sleep(3000); log.AppendLine("MARK saveas_new " + DateTime.UtcNow.Ticks);
  d.SaveAs(@"C:\wl\sp\m.rvt", new SaveAsOptions { OverwriteExistingFile = true });
  System.Threading.Thread.Sleep(3000); log.AppendLine("MARK saveas_overwrite " + DateTime.UtcNow.Ticks);
  d.SaveAs(@"C:\wl\sp\m.rvt", new SaveAsOptions { OverwriteExistingFile = true });
  System.Threading.Thread.Sleep(3000); log.AppendLine("MARK save_open " + DateTime.UtcNow.Ticks);
  using (var t = new Transaction(d, "touch")) { t.Start(); var l = new FilteredElementCollector(d).OfClass(typeof(Level)).FirstElement(); if (l != null) { var p = l.get_Parameter(BuiltInParameter.ALL_MODEL_MARK); if (p != null && !p.IsReadOnly) p.Set("sp"); } t.Commit(); }
  d.Save();
  System.Threading.Thread.Sleep(3000); log.AppendLine("MARK done " + DateTime.UtcNow.Ticks);
  d.Close(false); log.AppendLine("RESULT ok");
} catch (Exception ex) { log.AppendLine("RESULT fail " + ex.GetType().Name + ": " + ex.Message.Replace("\r", " ").Replace("\n", " ")); try { if (d != null) d.Close(false); } catch {} }
Console.WriteLine(log.ToString());
'''


def main(year, f):
    year = int(year); sid = hashlib.sha256(open(f, 'rb').read()).hexdigest()[:6]; tag = 'sp' + sid
    out = os.path.expanduser('~/c3x-tmp'); os.makedirs(out, exist_ok=True)
    with guest.vmlock():
        port = guest.fresh(year)
        if not port: print('no Revit port'); return 1
        guest.gssh('New-Item -ItemType Directory -Force C:\\wl\\sp | Out-Null; Remove-Item C:\\wl\\sp\\* -Force -Recurse -ErrorAction SilentlyContinue')
        guest.put(f, 'C:/wl/sp/src.rvt'); guest.put(os.path.join(HERE, 'rvt_save_timeline.ps1'), 'C:/wl/rvt_save_timeline.ps1')
        # poller in the background (detached guest process), 150 s
        guest.gssh("Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\\wl\\rvt_save_timeline.ps1','-Dir','C:\\wl\\sp','-Name','m.rvt','-Seconds','150','-Out','C:\\wl\\sp_timeline.csv' -WindowStyle Hidden")
        time.sleep(5)
        job = guest.run_job(year, port, JOB, tag, 300)
        time.sleep(max(0, 150 - 5 - 60))      # let the poller finish
        local = os.path.join(out, 'savepat_%s_%d.csv' % (sid, year)); got = guest.get('C:/wl/sp_timeline.csv', local)
        guest.down(year)
    res = 'RESULT ok' in job
    pats = {}
    if got and os.path.exists(local):
        rows = list(csv.DictReader(open(local, newline='')))
        pat, ev = classify(rows, 'm.rvt'); pats = (pat, ev)
        # also src.rvt is only read; side files and NTFS id changes are in ev
    row = '\t'.join([time.strftime('%Y-%m-%d %H:%M'), str(year), sid, 'job_ok=%s' % res, 'csv=%s' % got, str(pats)[:400]])
    open(os.path.expanduser('~/demo-state/rvt-save-pattern.tsv'), 'a').write(row + '\n'); print(row)
    return 0 if res and got else 1


if __name__ == '__main__': sys.exit(main(*sys.argv[1:3]))
