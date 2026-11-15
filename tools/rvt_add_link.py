"""rvt-ballet ADD LINK (clone-and-patch): duplicate an existing Revit link (symbol + instance + detail record, ids src..src+2) with new ids; same linked file. Derived from rvt_add_clone.py; Revit-made add pair (2020 and 2024 Autodesk samples) = exactly these 3 records.
Text notes etc: pass --nolatest."""
import sys,struct,os,argparse; sys.path.insert(0,'~/rvt-research/write-lab'); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
def _refuse_hook(t, v, tb):      # any unexpected failure (truncated / unreadable / non-RVT input) is a plain refusal, never a traceback; the build goes to a .part file so nothing is left behind
    if issubclass(t, (KeyboardInterrupt, SystemExit)): return sys.__excepthook__(t, v, tb)
    sys.stderr.write('REFUSED: input could not be read or edited safely (%s: %s); nothing written\n' % (t.__name__, str(v)[:120])); sys.exit(2)
sys.excepthook = _refuse_hook
os.environ['RVT_GEOM']='1'
import cfb as _cfb
_ps=sorted((n for n in _cfb.CFB(open(sys.argv[1],'rb').read()).streams() if n.startswith('Partitions/')),key=lambda n:int(n.split('/')[1])) if len(sys.argv)>1 and os.path.exists(sys.argv[1]) else []
if len(_ps)<=1 and os.environ.get('RVT_ADD_EDITENGINE') and any(os.environ.get(_k)=='1' for _k in ('HDR_SKIP','REC_SKIP','ITEM_SKIP')) and not os.environ.get('RVT_ADD_EDITENGINE_FORCE'):
    sys.exit('REFUSED: the edit engine on a single-partition project produced a file Revit 2024 rejects (CorruptModelException, HVAC 2024 2026-11-08); the default write-lab engine is the one with a Revit PASS. RVT_ADD_EDITENGINE_FORCE=1 overrides for experiments only')
_PROFILE_B = os.environ.get('RVT_ADD_PROFILE', 'B') == 'B' and len(_ps) <= 1 and not os.environ.get('RVT_ADD_EDITENGINE')      # default for single-partition since 2026-11-09: the former write-lab default (a1/DEF) is rejected by Revit 2024 (x2); RVT_ADD_PROFILE=A keeps it for experiments      # opt-in (c1x-rvtadd 2026-11-09): the only HVAC 2024 FI ADD layout Revit opened (bis/B_nomerge, x2): edit engine, header cut in at 259, insert NOT merged; readback of the new element still pending, so not the default
if _PROFILE_B:
    os.environ['RVT_ADD_EDITENGINE'] = '1'; os.environ['RVT_ADD_EDITENGINE_FORCE'] = '1'
    for _k in ('HDR_SKIP', 'REC_SKIP', 'ITEM_SKIP'): os.environ[_k] = '1'
    os.environ['INS_MERGE'] = '0'
if len(_ps)>1 or os.environ.get('RVT_ADD_EDITENGINE'):
    # multi-partition: the edit-lab engine (what rvtedit cp/aw/tn use) puts new items after the first few of each list (index 0 is special in real projects) and builds in the LAST big partition; the write-lab engine inserts at index 0 of partition 1
    sys.path.insert(0,os.path.expanduser('~/rvt-research/edit-lab'))
    for _k in ('HDR_SKIP','REC_SKIP','ITEM_SKIP'): os.environ.setdefault(_k,'1' if len(_ps)>1 else '0')      # single-partition: skip 0 reproduces the Revit-PASS write-lab bytes (HVAC 2024 a1, byte-identical, 2026-11-08); skip 1 = the rejected hvac_e/c12 layout
    _streams=_cfb.CFB(open(sys.argv[1],'rb').read()).streams()
    _big=[n for n in _ps if len(_streams[n].data)>20000]
    os.environ.setdefault('PART',(_big or _ps)[-1])
    import rvtgen_e as rvtgen
else:
    import rvtgen
import genlib
import rvt_idlist as idlist
ap=argparse.ArgumentParser(); ap.add_argument('seed'); ap.add_argument('out'); ap.add_argument('--src',type=int,required=True)
ap.add_argument('--dx',type=float,default=3.0); ap.add_argument('--dy',type=float,default=4.0); ap.add_argument('--dz',type=float,default=0.0); ap.add_argument('--nolatest',action='store_true'); ap.add_argument('--force',action='store_true',help='skip the dependents screen (instances that own children corrupt the model when copied)')
ap.add_argument('--base',type=int,default=0,help='first new id (internal, multi-partition passes)'); ap.add_argument('--members',default='012',help='which of symbol(0)/instance(1)/detail(2) this pass clones (internal)')
ap.add_argument('--same-file',action='store_true',help='allow the new link type to keep pointing at the SAME linked file as the source (Revit 2024 VM 2026-11-13: with the target beside the host BOTH link types then read not loaded; a clone with its own path loads fine). Edit the new link type path afterwards (rvtedit set_link_path) instead of using this')
a=ap.parse_args()
if not a.same_file and '--members' not in sys.argv and not os.environ.get('RVT_ADD_SAME_FILE'):
    sys.exit('REFUSED: the clone would point at the same linked file as the source link; Revit 2024 then fails to load BOTH link types when the file is present (VM-verified 2026-11-13). Re-run with --same-file only if you set a new path on the new link type afterwards')
if not os.environ.get('RVT_ADD_DAMAGED_FORCE'):      # a damaged input (bad gzip member / ECC page) was silently cloned into an 'ok' output (64 flipped bytes, 3 of 3 positions); refuse before building
    import rvt_scan as _S, rvt2text as _T, rvt_entities as _E
    _o = _S.load(a.seed)[0]; _bad = {}
    for _pn in ['/'.join(e) for e in _o.listdir(streams=True)]:
        if _pn.startswith('Partitions/'):
            _n = _T.damaged_members(_o.openstream(_pn).read())
            if _n: _bad[_pn] = _n
    _ecc = _E.ecc_bad_pages(_o)
    if _bad or _ecc: sys.exit('REFUSED: input file is damaged (gzip members %s, ECC-bad pages %d); a clone of it would carry the damage; nothing written' % (_bad, len(_ecc)))
import math
for _n,_v in (('dx',a.dx),('dy',a.dy),('dz',a.dz)):
    if not math.isfinite(_v) or (abs(_v)>1e6 and not os.environ.get('RVTEDIT_ALLOW_FAR')): sys.exit('REFUSED: --%s=%r is not finite or is beyond 1e6 ft (same rule as rvtedit)'%(_n,_v))
if os.path.realpath(a.seed)==os.path.realpath(a.out): sys.exit('REFUSED: output path equals the input file; ADD writes a copy only (in-place overwrite goes through the savegate path)')
if os.path.exists(a.out) and (os.path.samefile(a.seed, a.out) or os.stat(a.out).st_nlink > 1): sys.exit('REFUSED: output {} is the input file or a hard link of some file (writing it would change the original in place); pick a fresh output path'.format(os.path.basename(a.out)))
if not os.environ.get('RVT_ADD_WORKSHARED_FORCE'):      # workshared (central/local) models carry worksets + a central link the writer does not maintain: same rule as the in-place save (save.py Workshared)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from rvtballet.save import worksharing_state
    _ws = worksharing_state(open(a.seed, 'rb').read())
    if not (_ws or '').startswith('Not enabled'): sys.exit('REFUSED: Worksharing state of %s is %r (not "Not enabled"): ADD would create elements without worksets / central bookkeeping. RVT_ADD_WORKSHARED_FORCE=1 for experiments' % (os.path.basename(a.seed), _ws))
if not a.force:
    sys.path.insert(0,os.path.expanduser('~/rvt-research/edit-lab')); sys.path.insert(0,os.path.expanduser('~/rvt-research'))
    import rvtedit
    _ed=rvtedit.Edit(a.seed)
    for _i,_want in ((a.src,'RvtLinkSymbol'),(a.src+1,'RvtLinkInstance')):
        if _i not in _ed.g.e.m.ids: sys.exit('REFUSED: no element with id %d in %s'%(_i,a.seed))
        _c=_ed.g.e.trace(_i)[2]['class']
        if _c!=_want: sys.exit('REFUSED: element %d is a %s, expected %s: --src must be the RvtLinkSymbol of an existing link whose instance and detail record directly follow it (ids src+1, src+2; seen in every Autodesk 2020/2024 sample and in Revit-made adds)'%(_i,_c,_want))
    if a.src+2 not in _ed.g.e.m.ids: sys.exit('REFUSED: no element with id %d (third record of the link)'%(a.src+2))
    print('link triple screen ok: symbol %d, instance %d, detail %d'%(a.src,a.src+1,a.src+2))
g=rvtgen.Gen(a.seed)
if a.src not in g.e.m.ids or a.src<=0: sys.exit('REFUSED: no element with id %d in %s'%(a.src,a.seed))
if g.nextid<=g.maxid and not a.force: raise SystemExit('refuse: ElemTable counter %d <= max element id %d (new id would collide); --force to override'%(g.counter,g.maxid))
W=g.W; S0=a.src; MEM=[int(c) for c in a.members]; S=S0+MEM[0]
try: T=g.template(S)
except IndexError:
    T=None
    for _pn in [x for x in g.e.m.parts if x!=getattr(g,'pn',None)]:
        try: _g2=rvtgen.Gen(a.seed,part=_pn)
        except TypeError:      # edit-engine Gen (rvtgen_e) takes the partition from $PART
            os.environ['PART']=_pn; _g2=rvtgen.Gen(a.seed)
        try: T=_g2.template(S); print('source %d lives in %s: template only, building in the default partition'%(S,_pn)); break
        except IndexError: pass
if T is None: sys.exit('REFUSED: source %d has no element header in the first partition (%s); the writer only addresses the first partition of a multi-partition file. Pick a source stored there.'%(S,list(g.e.m.parts)[0]))
trip=[S0,S0+1,S0+2]
def _tmpl(sid):
    try: return g.template(sid)
    except IndexError: pass
    for _pn in [x for x in g.e.m.parts if x!=getattr(g,'pn',None)]:
        try: _g2=rvtgen.Gen(a.seed,part=_pn)
        except TypeError:
            os.environ['PART']=_pn; _g2=rvtgen.Gen(a.seed)
        try: return _g2.template(sid)
        except IndexError: pass
    sys.exit('REFUSED: no element header for %d in any partition'%sid)
et=g._et(); RW=g.RW; n_=struct.unpack_from('<I',et,2)[0]
best=max(range(n_),key=lambda k:(struct.unpack_from('<I',et,6+RW*k+12)[0],struct.unpack_from('<I',et,6+RW*k+8)[0]))
tr=struct.unpack_from('<3I',et,6+RW*best+8)
base=a.base or g.nextid; news=[base,base+1,base+2]; g.nextid=max(g.nextid,base+3)
mp=dict(zip(trip,news))
import zlib
for k,sid in enumerate(trip):
    if k not in MEM: continue
    Tk=_tmpl(sid)
    rec=bytearray(Tk['rec']); hdr=bytearray(Tk['hdr']); item=bytearray(Tk['item']); row=bytearray(Tk['row'])
    for o,n in mp.items():
        for buf in (rec,hdr,item,row): genlib.rep(buf,struct.pack(g.IDF,o),struct.pack(g.IDF,n))
    # the header's deletion list (N entries of 22 bytes after the 6-byte prefix) names the SOURCE's dependents (views, tags ...): the clone owns none; a Revit-made new link has N=0 (measured 2020 + 2024 pairs: header 193/183/175 B with N=0, the source link in HVAC 413/337/219 B with N=10/7/2)
    _n=struct.unpack_from('<I',hdr,14)[0]      # hdr = id(8) + body size(4) + body (tag = g.EHT, ElementHeader schema index + 12: 0x059f in 2024, 0x05e5 in 2026, count, entries ...)
    if _n:
        assert bytes(hdr[12:14])==g.EHT and struct.unpack_from('<I',hdr,8)[0]==len(hdr)-12 and 18+22*_n<=len(hdr),'header layout'
        del hdr[18:18+22*_n]; struct.pack_into('<I',hdr,14,0); struct.pack_into('<I',hdr,8,len(hdr)-12)
    rec=g.stamp(bytes(rec))
    assert struct.unpack_from('<I',item,W+4)[0]==len(item)-(W+8),'item layout'
    struct.pack_into('<I',item,W,zlib.adler32(bytes(item[W+8:]))&0xffffffff)
    struct.pack_into('<3I',row,8,*tr)
    g.new.append((bytes(hdr),rec,bytes(item),news[k])); g.rows.append(bytes(row))
    print('cloned',sid,'->',news[k],len(rec),'B')
nid=news[0]
if not a.nolatest:
    def reg(raw):
        hit=0
        for o,n in mp.items():
            if trip.index(o) not in MEM: continue
            raw,Ls=idlist.add_to_lists(raw,o,n,W); hit+=len(Ls); print('latest lists for',o,[(l[2]) for l in Ls])
        if not hit: sys.exit('REFUSED: the link symbol appears in no Global/Latest id-list; nothing written')
        return raw
    g.latest_edits=[('Latest',reg)]
g.itag=T['item'][W+8:W+10]
if a.base: print('PASSIDS',news)
g.itag=T['item'][W+8:W+10]
_final = os.path.realpath(a.out); _b, _x = os.path.splitext(os.path.basename(_final)); a.out = os.path.join(os.path.dirname(os.path.abspath(_final)), '.' + _b + '.%d.part' % os.getpid() + _x)      # build beside the target, move into place only after every check passes: a refused/failed build must not destroy a previous output
if os.path.exists(_final) and not os.access(_final, os.W_OK): sys.exit('REFUSED: the output file %s exists and is read-only; it was not overwritten (clear the read-only flag or pick another name)' % os.path.basename(_final))      # c1x-rvtsave 194: a read-only previous output was silently replaced (and made writable)
import atexit; atexit.register(lambda: os.path.exists(a.out) and os.remove(a.out))
g.commit(a.out)
# fail-closed layout check (c1x-rvtadd 2026-11-08): Revit 2024 rejected two outputs whose first gzip member of the partition was split mid header region (insert did not fit LIMIT). Compare with the source.
if not os.environ.get('RVT_ADD_LAYOUT_FORCE'):
    try:
        import rvtgen as _rg
        _src = _rg.Gen(a.seed); _dst = _rg.Gen(a.out)
        for _pn in sorted(n for n in _src.e.m.parts if n.startswith('Partitions/')):
            _o = _src.e.part(_pn).offs(); _n = _dst.e.part(_pn).offs()
            if len(_o) > 2 and len(_n) > 2 and _o[1] > 20000 and not (_n[1] - _n[0] >= _o[1] - _o[0] or _n[2] - _n[1] == _o[1] - _o[0] or (_PROFILE_B and len(_n) > 3 and (_n[1] - _n[0]) + (_n[3] - _n[2]) == _o[1] - _o[0])):      # the original first member must survive whole (grown in place or pushed back intact)
                os.remove(a.out); sys.exit('REFUSED: %s first member was split (%d B no longer present as one member in the first 8; new first members start %s): Revit rejects this layout (CorruptModelException); output removed. RVT_ADD_LAYOUT_FORCE=1 to keep it for experiments' % (_pn, _o[1], _n[:4]))
    except SystemExit: raise
    except Exception as _e: os.remove(a.out); sys.exit('REFUSED: layout check failed (%s); output removed' % _e)
try:      # the OUTPUT must itself be free of damaged gzip members / ECC-bad pages (a writer bug would otherwise ship a self-damaged file as ok)
    import rvt_scan as _S2, rvt2text as _T2, rvt_entities as _E2
    _o2 = _S2.load(a.out)[0]; _b2 = {}
    for _pn2 in ['/'.join(e) for e in _o2.listdir(streams=True)]:
        if _pn2.startswith('Partitions/'):
            _n2 = _T2.damaged_members(_o2.openstream(_pn2).read())
            if _n2: _b2[_pn2] = _n2
    _e2 = _E2.ecc_bad_pages(_o2)
    if _b2 or _e2: os.remove(a.out); sys.exit('REFUSED: the built output is damaged (gzip members %s, ECC-bad pages %d); output removed' % (_b2, len(_e2)))
except SystemExit: raise
except Exception as _x: os.remove(a.out); sys.exit('REFUSED: output integrity check failed (%s); output removed' % _x)
os.replace(a.out, _final)
print('ok',_final,'new id',nid)
