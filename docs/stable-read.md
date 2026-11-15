# Reading a .rvt that may be saved at the same time (torn reads)

Guarantee (rvtballet/stable.py, used by `rvt-ballet <query>`, info, counts, diff, check): a command never prints an answer derived from a file that
changed while it was read. Instead it prints one line and exits 75 (changed / still being saved, retry) or 1 (not a complete file).

What is checked, in order, for every .rvt/.rte/.rfa argument:
1. quiet period: modified less than 5 s ago (`--quiet-secs N`, env RVTBALLET_QUIET, 0 = off), stat still moving, or a fresh side file next to it
   (`<name>.NNNN.rvt`, `*.tmp`, `*.lock`...): wait with backoff (up to 6 retries), then refuse (exit 75).
2. entry fingerprint: size, mtime_ns, inode, device and a hash of 18 sampled blocks (head 64 KB, tail 64 KB, 16 spread 4 KB blocks); compound-file
   header/FAT check (truncated or zero length files refused).
3. exit fingerprint, compared with the entry one; any difference replaces the answer (also replaces a parse error caused by the tear).
4. fastquery additionally compares the open handle and the path after every query (existing check, now the same exception type).

`--snapshot`: copy to a private temp dir (needs free disk of the file size; a 1 GB copy from /mnt/c takes about 60-90 s, not measured here), accept
the copy only when the source fingerprint is equal before and after and the copy matches size and sampled blocks, query the copy, delete it.

Measured overhead, unchanged 22 MB HVAC sample: guard 2 ms (fingerprint 0.7 ms, header/FAT check 4.5 ms); both are independent of file size
except the FAT read (1 MB per GB). Measured on a 1 GB random file on local disk, page cache warm: fingerprint 0.6 to 1.2 ms per call (two per query), so well under 0.1 s; cold-cache and 9p cost not measured.

Not guaranteed: a writer that rewrites bytes BETWEEN the sampled blocks without changing size or mtime_ns and finishes inside one query is only
caught by `--snapshot` (which compares size and samples, not every byte either); a file system with coarse mtime (FAT, some 9p/SMB caches) weakens
check 1 and 3; Windows share modes are invisible from WSL; side files are only seen if the share lists them.

Observed Revit write pattern: NOT measured yet (no VM lane free). The tests emulate in-place chunked overwrite (also with mtime restored),
truncate then rewrite, temp file plus atomic rename, append, symlink swap.

Strict mode: RVTBALLET_FULL_HASH=1 makes the fingerprint hash the whole file (catches a rewrite between sampled blocks with the mtime restored; costs one full read of the file, so about the snapshot copy time).

Zero regions: a file that was extended (preallocated) and not yet filled, or has a hole from an interrupted copy, looks structurally valid to the FAT check. `cfb_check` also refuses a file whose last 64 KB are all zero or in which two or more of the 16 spread sampled blocks are all zero (none of 1080 sampled blocks in 60 real files were; RVTBALLET_ALLOW_ZERO_BLOCKS=1 accepts a genuine exception). Not caught: a zero hole smaller than the sampled blocks (for example the last 4 KB only); the gzip CRC of the segments that a query really reads still catches those it touches.
