"""rvt-ballet file helpers shared by the query engine (fastquery), the CLI (infocli: info, diff, check) and the edit tools: import paths, decoder memory
hygiene, signed ids, header-only file information (BasicFileInfo, project information, editors, save records: no partition is touched) and the reduction
of admin records. Moved here from fastinfo.py when its scan was replaced by fastquery.scan (2026-11-14)."""
import os, sys, re, struct, io, zipfile, collections, time

def _tune():
    """memory hygiene for the Rust decoder: one decode thread (RVT_THREADS) and one malloc arena; measured on a 15 MB file whose 17k ElementHeaders hold 60 KB trees each: peak 1.9 GB -> 0.43 GB"""
    os.environ.setdefault('RVT_THREADS', '1')
    try:
        import ctypes; ctypes.CDLL('libc.so.6').mallopt(-8, 1)       # M_ARENA_MAX
    except Exception: pass



def _rss_mb():
    try:
        return int(open('/proc/self/statm').read().split()[1]) * os.sysconf('SC_PAGE_SIZE') >> 20
    except Exception: return -1



def _trim():
    try:
        import ctypes; ctypes.CDLL('libc.so.6').malloc_trim(0)
    except Exception: pass



def _paths():
    for p in (os.environ.get('RVT_READER_DIR'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/src/rvt-core/python')):
        if p and os.path.isdir(p) and p not in sys.path: sys.path.append(p)
    try:
        from . import plat   # noqa: F401  (adds the sibling rvt-core / rvt-sheets dirs to sys.path)
    except Exception: pass



def basic_info(o):
    b = o.openstream('BasicFileInfo').read(); i = b.find('Worksharing'.encode('utf-16le'))
    t = b[i:].decode('utf-16le', 'ignore') if i >= 0 else b.decode('utf-16le', 'ignore')
    d = collections.OrderedDict()
    for l in re.split(r'[\r\n]+', t):
        if ':' in l:
            k, v = l.split(':', 1); d[k.strip()] = v.strip()
    return d



def project_information(o, names):
    if 'ProjectInformation' not in names: return {}
    try:
        z = zipfile.ZipFile(io.BytesIO(o.openstream('ProjectInformation').read()))
        x = z.read(z.namelist()[0]).decode('utf-8', 'replace')
    except Exception: return {}
    out = {}
    for tag in ('title', 'BuildingName', 'OrganizationName', 'OrganizationDescription', 'Author', 'ProjectNumber', 'ProjectName', 'ProjectIssueDate', 'ProjectStatus', 'ClientName', 'Address'):
        m = re.search(r'<%s>([^<]*)</%s>' % (tag, tag), x, re.I)
        if m and m.group(1).strip(): out[tag] = m.group(1).strip()
    return out



def saves(o):
    """[(user, unix time)] from Global/DocumentIncrementTable: each save record is the user name (UTF-16) followed by 4 zero bytes, two ids, a zero u32 and the save time as unix seconds
    (verified against file mtimes of 4 seed files; implausible values are dropped)"""
    import rvtfmt
    PR = re.compile(rb'(?:[\x20-\x7e]\x00){3,}'); out = []
    try:
        pre, d, _ = rvtfmt.inflate_stream(o.openstream('Global/DocumentIncrementTable').read())
        for m in PR.finditer(d):
            if m.end() + 20 > len(d): continue
            ts = struct.unpack_from('<I', d, m.end() + 16)[0]
            if 1.0e9 < ts < 2.2e9: out.append((m.group().decode('utf-16le'), ts))
    except Exception: pass
    return out



def editors(o):
    import rvtfmt
    PR = re.compile(rb'(?:[\x20-\x7e]\x00){3,}')
    try:
        pre, dit, _ = rvtfmt.inflate_stream(o.openstream('Global/DocumentIncrementTable').read())
        c = collections.Counter(m.group().decode('utf-16le') for m in PR.finditer(dit))
        return [u for u, n in c.most_common() if re.search(r'[A-Za-z]{3}', u)][:30]
    except Exception: return []



_KEEP = {'Family': ('m_categoryId',), 'ProjectRevision': ('m_description', 'm_date', 'm_numberStr', 'm_sequenceNumber', 'm_issuedBy', 'm_issuedTo', 'm_issued'), 'Level': ('m_text',), 'Grid': ('m_text',), 'ProjectPhase': ('m_name',), 'ProjectInfo': ('m_text', 'm_name'), 'Viewport': ('m_dbViewId',), 'FamilySurrogate': ('m_categoryId', 'm_elemId'), 'FamSymSurrogate': ('m_categoryId', 'm_elemId'), 'GStyleElem': ('m_categoryId',), 'CategoryElem': ('m_ownerId',), 'ViewSheetSet': ('m_name', 'm_orderedViewSheetList')}
_KEEP_VIEW = ('m_viewName', 'm_sheetNumber', 'm_issueDate', 'm_drawnBy', 'm_sheetViewportElemIds', 'm_isTemplate', 'm_scale', 'm_text', 'm_name', 'm_approvedBy', 'm_explicitlyPresentRevisionIds', 'm_revNumMap', 'm_dbDrawingId')


def _reduce(c, rec):
    """keep only the fields the lists need: DBView/ViewSchedule records are large trees (the retained full records were ~250 MB of the baseline RSS on a 900 MB file)"""
    f = rec['fields']; keep = _KEEP_VIEW if c.startswith('DBView') else _KEEP.get(c, ())
    out = {k: f[k] for k in keep if k in f}
    if c == 'CategoryElem':
        pc = f.get('m_pCategory'); pc = pc.get('obj', pc) if isinstance(pc, dict) else pc
        if isinstance(pc, dict): out['m_parentCategoryId'] = pc.get('m_parentCategoryId'); out['m_name'] = pc.get('m_name')
    if c == 'Level':
        ps = f.get('m_pSurface'); ps = ps.get('obj', ps) if isinstance(ps, dict) else ps
        if isinstance(ps, dict) and 'm_origin' in ps: out['m_pSurface'] = {'m_origin': list(ps['m_origin'])}
    return {'id': rec['id'], 'fields': out}


def _plausible(v, W):
    v = _sc(v, W); return -(1 << 31) <= v < (1 << 31)


def _sc(v, W):
    v = int(v); return v - (1 << (8 * W)) if v >= 1 << (8 * W - 1) else v


def file_info(path):
    """seconds: BasicFileInfo, project information, editors. No partition is touched."""
    _paths()
    import olefile
    o = olefile.OleFileIO(path); names = ['/'.join(e) for e in o.listdir(streams=True)]
    r = {'file_size': os.path.getsize(path), 'info': dict(basic_info(o)), 'project': project_information(o, names), 'editors': editors(o),
         'partitions': sum(1 for n in names if n.startswith('Partitions/'))}
    sv = saves(o)
    if sv:
        u, t = max(sv, key=lambda x: x[1]); r['last_saved_by'] = u; r['last_saved'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t)) + ' UTC'
        r['first_saved'] = time.strftime('%Y-%m-%d', time.gmtime(min(x[1] for x in sv))); r['save_records'] = len(sv)
    r['mtime'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(path)))
    return r


def elements_from_index(path, build=False):
    """opt-in fast path (does not touch scan): per-element arrays from the persistent element index (rvtballet.elemindex) in ~20 ms once built.
    -> {id, cat (raw builtin/sub-category id as in the ElementHeader, -1 none), owner_view, family, class_tag, has_header} or None when no up-to-date index exists (cache key = path/size/mtime/inode/ctime)
    and build is False. cat is RAW (positive ids are CategoryElem ids); cat_resolved equals the resolved builtin category of scan() (-2**62 = none) for indexes built after 2026-11-14."""
    from . import elemindex as EI
    try: idx = EI.load(path)
    except (FileNotFoundError, OSError):
        if not build: return None
        idx = EI.build(path)
    return {"id": idx["id"], "cat": idx["cat"], "cat_resolved": idx.get("cat_resolved"), "owner_view": idx["ownerview"], "family": idx["family"], "class_tag": idx["tag"], "has_header": idx["has_header"]}
