# Guest-side poller (run in the offline Revit VM while Revit Saves / SaveAs / autosaves a project): logs the folder state every 20 ms.
# usage: powershell -File rvt_save_timeline.ps1 -Dir C:\work -Name model.rvt -Seconds 120 -Out C:\work\timeline.csv
# One CSV row per change: t_ms, name, length, lastwrite_ticks, fileindex (NTFS id: changes when the file is replaced by rename), and a 'GONE' row when a file disappears.
# Reading this CSV shows: in place overwrite (same fileindex, length/lastwrite change in steps), truncate+rewrite (length drops, then grows),
# temp+rename (new name appears, then the target's fileindex changes), side files (backup folder, <name>.NNNN.rvt, *.tmp).
param([string]$Dir, [string]$Name, [int]$Seconds = 120, [string]$Out = "timeline.csv")
Add-Type -MemberDefinition '[DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)] public static extern IntPtr CreateFile(string f,uint a,uint s,IntPtr sa,uint d,uint fl,IntPtr t); [DllImport("kernel32.dll")] public static extern bool GetFileInformationByHandle(IntPtr h, out BY_HANDLE_FILE_INFORMATION i); [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h); [StructLayout(LayoutKind.Sequential)] public struct BY_HANDLE_FILE_INFORMATION { public uint Attr; public uint CL; public uint CH; public uint AL; public uint AH; public uint WL; public uint WH; public uint Vol; public uint SH; public uint SL; public uint Links; public uint IH; public uint IL; }' -Name K -Namespace W
function FileId($p) {
  $h = [W.K]::CreateFile($p, 0, 7, [IntPtr]::Zero, 3, 0x02000000, [IntPtr]::Zero)   # no access, share all, backup semantics: never blocks Revit
  if ($h -eq [IntPtr](-1)) { return "noaccess" }
  $i = New-Object W.K+BY_HANDLE_FILE_INFORMATION; [void][W.K]::GetFileInformationByHandle($h, [ref]$i); [void][W.K]::CloseHandle($h)
  return ("{0:x}{1:x8}" -f $i.IH, $i.IL)
}
$sw = [Diagnostics.Stopwatch]::StartNew(); $last = @{}; $rows = New-Object Collections.Generic.List[string]; $rows.Add("t_ms,name,length,lastwrite_ticks,fileindex"); $flushed = 0; $lastFlush = 0
while ($sw.Elapsed.TotalSeconds -lt $Seconds) {
  $now = @{}
  try {
    foreach ($fp in [IO.Directory]::EnumerateFiles($Dir, '*', [IO.SearchOption]::AllDirectories)) {
      try { $fi = New-Object IO.FileInfo $fp; $k = $fp.Substring($Dir.Length).TrimStart('\'); $now[$k] = "{0},{1},{2}" -f $fi.Length, $fi.LastWriteTimeUtc.Ticks, (FileId $fp) } catch { if ($rows.Count -lt 4) { $rows.Add("{0},FILEERR {1},,," -f $sw.ElapsedMilliseconds, ($_.Exception.Message -replace '[,\r\n]',' ')) } }
    }
  } catch { if ($rows.Count -lt 3) { $rows.Add("{0},ENUMERR {1},,," -f $sw.ElapsedMilliseconds, ($_.Exception.Message -replace '[,\r\n]',' ')) } }
  foreach ($k in $now.Keys) { if ($last[$k] -ne $now[$k]) { $rows.Add("{0},{1},{2}" -f $sw.ElapsedMilliseconds, $k, $now[$k]) } }
  foreach ($k in @($last.Keys)) { if (-not $now.ContainsKey($k)) { $rows.Add("{0},{1},GONE,," -f $sw.ElapsedMilliseconds, $k) } }
  $last = $now
  if ($sw.ElapsedMilliseconds - $lastFlush -gt 1000) {   # incremental flush: a killed poller still leaves a CSV
    $lastFlush = $sw.ElapsedMilliseconds; $rows | Set-Content -Encoding ASCII $Out
  }
  Start-Sleep -Milliseconds 20
}
$rows | Set-Content -Encoding ASCII $Out
