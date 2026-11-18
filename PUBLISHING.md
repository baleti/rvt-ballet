# Publishing policy

This repository is public. Progress, handoffs, notes and docs belong in it as normal.

Confidential material must NOT be committed. That means: office or employer project files, names and paths,
client or project identifiers, personal or private information, credentials, personal email addresses, and
internal host names or IP addresses. Keep it in a `private/` directory in your working copy (listed in
`.git/info/exclude`, never committed) and refer to it in tracked files by generic names only
(for example `office-A`, `projectQ`, `office-model`, `<private-corpus>`, `remote-host`).

Commit with the noreply identity `<user>@users.noreply.github.com`. Never commit sample or customer models
(`.rvt`, `.rfa`, `.dwg`, ...), generated outputs, logs or caches.
