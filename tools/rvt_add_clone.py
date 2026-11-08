"""rvt-ballet ADD (clone-and-patch): clone an existing FamilyInstance (--src) in a project, new id, moved by dx,dy,dz; Latest id-lists containing src get the new id.
Text notes etc: pass --nolatest."""
import sys,struct,os,argparse; sys.path.insert(0,'~/rvt-research/write-lab'); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
os.environ['RVT_GEOM']='1'
import cfb as _cfb
_ps=sorted((n for n in _cfb.CFB(open(sys.argv[1],'rb').read()).streams() if n.startswith('Partitions/')),key=lambda n:int(n.split('/')[1])) if len(sys.argv)>1 and os.path.exists(sys.argv[1]) else []
if len(_ps)<=1 and os.environ.get('RVT_ADD_EDITENGINE') and not os.environ.get('RVT_ADD_EDITENGINE_FORCE'):
    sys.exit('REFUSED: the edit engine on a single-partition project produced a file Revit 2024 rejects (CorruptModelException, HVAC 2024 2026-11-08); the default write-lab engine is the one with a Revit PASS. RVT_ADD_EDITENGINE_FORCE=1 overrides for experiments only')
if len(_ps)>1 or os.environ.get('RVT_ADD_EDITENGINE'):
    # multi-partition: the edit-lab engine (what rvtedit cp/aw/tn use) puts new items after the first few of each list (index 0 is special in real projects) and builds in the LAST big partition; the write-lab engine inserts at index 0 of partition 1
    sys.path.insert(0,os.path.expanduser('~/rvt-research/edit-lab'))
    for _k in ('HDR_SKIP','REC_SKIP','ITEM_SKIP'): os.environ.setdefault(_k,'1')
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
a=ap.parse_args()
import math
for _n,_v in (('dx',a.dx),('dy',a.dy),('dz',a.dz)):
    if not math.isfinite(_v) or (abs(_v)>1e6 and not os.environ.get('RVTEDIT_ALLOW_FAR')): sys.exit('REFUSED: --%s=%r is not finite or is beyond 1e6 ft (same rule as rvtedit)'%(_n,_v))
if os.path.realpath(a.seed)==os.path.realpath(a.out): sys.exit('REFUSED: output path equals the input file; ADD writes a copy only (in-place overwrite goes through the savegate path)')
if not a.force:
    sys.path.insert(0,os.path.expanduser('~/rvt-research/edit-lab')); sys.path.insert(0,os.path.expanduser('~/rvt-research'))
    import rvtedit
    _ed=rvtedit.Edit(a.seed)
    if a.src<=0 or a.src not in _ed.g.e.m.ids: sys.exit('REFUSED: no element with id %d in %s'%(a.src,a.seed))
    _deps=_ed.dependents(a.src)
    # classes with Revit evidence (HVAC 2024: source 1365188 owns 4 RbsHvacSystem + 2 IndependentTag, its clone opened clean, +1 equipment): tolerated; anything else refuses
    _OK=('RbsHvacSystem','IndependentTag'); _bad=[(d,_ed.g.e.trace(d)[2]['class']) for d in _deps]; _bad=[x for x in _bad if x[1] not in _OK]
    if _bad: sys.exit('REFUSED: source %d owns dependent element(s) %s (header deletion lists name it); copying it corrupts the model. Pick a childless source or --force.'%(a.src,_bad[:6]))
    _c=_ed.g.e.trace(a.src)[2]['class']
    if _c != 'FamilyInstance': sys.exit('REFUSED: source %d is a %s; this tool moves FamilyInstance origins only (a %s copy would sit on the original and skip owner-view/host lists). Text notes: rvtedit.py tn:X:Y:TEXT; other classes need their own op.' % (a.src, _c, _c))
    print('dependents screen: none')
g=rvtgen.Gen(a.seed)
if a.src not in g.e.m.ids or a.src<=0: sys.exit('REFUSED: no element with id %d in %s'%(a.src,a.seed))
if g.nextid<=g.maxid and not a.force: raise SystemExit('refuse: ElemTable counter %d <= max element id %d (new id would collide); --force to override'%(g.counter,g.maxid))
W=g.W; S=a.src
try: T=g.template(S)
except IndexError:
    T=None
    for _pn in [x for x in g.e.m.parts if x!=getattr(g,'pn',None)]:
        try: _g2=rvtgen.Gen(a.seed,part=_pn)
        except TypeError:      # edit-engine Gen (rvtgen_e) takes the partition from $PART
            os.environ['PART']=_pn; _g2=rvtgen.Gen(a.seed)
        try: T=_g2.template(S); g=_g2; print('source %d lives in %s: building there'%(S,_pn)); break
        except IndexError: pass
if T is None: sys.exit('REFUSED: source %d has no element header in the first partition (%s); the writer only addresses the first partition of a multi-partition file. Pick a source stored there.'%(S,list(g.e.m.parts)[0]))
idS=struct.pack(g.IDF,S)
L={n:(o,e) for n,o,e,_ in T['log']}
et=g._et(); RW=g.RW; n_=struct.unpack_from('<I',et,2)[0]
best=max(range(n_),key=lambda k:(struct.unpack_from('<I',et,6+RW*k+12)[0],struct.unpack_from('<I',et,6+RW*k+8)[0]))
tr=struct.unpack_from('<3I',et,6+RW*best+8)
nid=g.nextid; g.nextid+=1; idN=struct.pack(g.IDF,nid)
rec=bytearray(T['rec']); print('src id occurrences in rec',rec.count(idS)); genlib.rep(rec,idS,idN)
nmv=0
for n,o,e,v in T['log']:
    if n in ('FamilyInstance.m_instOrigin','Trf.m_or'):
        x,y,z=struct.unpack_from('<3d',rec,o); struct.pack_into('<3d',rec,o,x+a.dx,y+a.dy,z+a.dz); nmv+=1
print('moved fields',nmv)
rec=g.stamp(bytes(rec))
hdr=bytearray(T['hdr']); genlib.rep(hdr,idS,idN)
item=bytearray(T['item']); genlib.rep(item,idS,idN)
import zlib
assert struct.unpack_from('<I',item,W+4)[0]==len(item)-(W+8),'item layout'
struct.pack_into('<I',item,W,zlib.adler32(bytes(item[W+8:]))&0xffffffff)
row=bytearray(T['row']); genlib.rep(row,idS,idN); struct.pack_into('<3I',row,8,*tr)
g.new.append((bytes(hdr),rec,bytes(item),nid)); g.rows.append(bytes(row))
if not a.nolatest:
    def reg(raw):
        out,Ls=idlist.add_to_lists(raw,S,nid,W); print('latest lists',[(l[2]) for l in Ls]); assert Ls,'no id-list found'; return out
    g.latest_edits=[('Latest',reg)]
g.itag=T['item'][W+8:W+10]
g.commit(a.out)
# fail-closed layout check (c1x-rvtadd 2026-11-08): Revit 2024 rejected two outputs whose first gzip member of the partition was split mid header region (insert did not fit LIMIT). Compare with the source.
if not os.environ.get('RVT_ADD_LAYOUT_FORCE'):
    try:
        import rvtgen as _rg
        _src = _rg.Gen(a.seed); _dst = _rg.Gen(a.out)
        for _pn in sorted(n for n in _src.e.m.parts if n.startswith('Partitions/')):
            _o = _src.e.part(_pn).offs(); _n = _dst.e.part(_pn).offs()
            if len(_o) > 2 and len(_n) > 2 and _o[1] > 20000 and not (_n[1] - _n[0] >= _o[1] - _o[0] or _n[2] - _n[1] == _o[1] - _o[0]):      # the original first member must survive whole (grown in place or pushed back intact)
                os.remove(a.out); sys.exit('REFUSED: %s first member was split (%d B no longer present as one member in the first 8; new first members start %s): Revit rejects this layout (CorruptModelException); output removed. RVT_ADD_LAYOUT_FORCE=1 to keep it for experiments' % (_pn, _o[1], _n[:4]))
    except SystemExit: raise
    except Exception as _e: os.remove(a.out); sys.exit('REFUSED: layout check failed (%s); output removed' % _e)
print('ok',a.out,'new id',nid)
