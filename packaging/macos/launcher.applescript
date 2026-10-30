-- droplet: starts rvt-ballet on the dropped / double clicked .rvt files, or the start page (serve) without files
on run
	my launch({})
end run

on open theFiles
	my launch(theFiles)
end open

on launch(theFiles)
	set res to POSIX path of (path to resource "app") & "/.."
	set py to quoted form of (res & "/python/bin/python3")
	set sub to " serve"
	set args to ""
	if (count of theFiles) > 0 then set sub to " open"
	repeat with f in theFiles
		set args to args & " " & quoted form of POSIX path of f
	end repeat
	do shell script "cd " & quoted form of (res & "/app") & " && nohup " & py & " -m rvtballet" & sub & args & " >/dev/null 2>&1 &"
end launch
