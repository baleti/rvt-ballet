#!/usr/bin/env python3
"""rvt_poller_diag.py : run tools/rvt_save_timeline.ps1 in the FOREGROUND in the offline guest for 6 s over a dummy file (no Revit started) and print the CSV + errors.
Takes the normal FIFO guest.vmlock; synthetic data only."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); os.environ['STAGEB'] = '1'
import guest
with guest.vmlock():
    print('lane alive:', guest.lane_alive(), flush=True)
    r = guest.gssh('New-Item -ItemType Directory -Force C:\\wl\\spd | Out-Null; Remove-Item C:\\wl\\spd\\* -Force -Recurse -ErrorAction SilentlyContinue; Set-Content -Path C:\\wl\\spd\\m.rvt -Value "hello"; Get-ChildItem C:\\wl\\spd | Out-String'); print(r.stdout, r.stderr)
    guest.put(os.path.join(HERE, 'rvt_save_timeline.ps1'), 'C:/wl/rvt_save_timeline.ps1')
    r = guest.gssh('powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\wl\\rvt_save_timeline.ps1 -Dir C:\\wl\\spd -Name m.rvt -Seconds 6 -Out C:\\wl\\spd_t.csv 2>&1 | Out-String; "--- csv"; Get-Content C:\\wl\\spd_t.csv | Out-String', 90)
    print(r.stdout[-3000:], r.stderr[-800:])
