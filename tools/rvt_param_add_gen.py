"""param-only add on an ARBITRARY 2024 project (experiment; Autodesk samples only): usage gen.py SEED OUT"""
import sys,os,re,struct,json
os.environ.setdefault('RVTGEN_INPLACE','1')      # insert into the existing member (Revit's own way); the default append path produces CArchiveException 105 on Structural 2024
import uuid as _uuid
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
import cfb as _cfb
if len(sys.argv) != 3: sys.exit('usage: rvt_param_add_gen.py SEED OUT')
if os.path.realpath(sys.argv[1]) == os.path.realpath(sys.argv[2]): sys.exit('REFUSED: output path equals the input file; nothing written')
try: _fy = int(re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(sys.argv[1], 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file; nothing written')
if _fy != 2024: sys.exit('REFUSED: parameter add is only built for Revit 2024 files (this file is %d); nothing written' % _fy)
WL=os.path.expanduser('~/rvt-research/write-lab'); sys.path.insert(0,WL)
import rvtgen,genlib,genlib2,wledit,scenes
Y=2024; genlib2.YEAR=Y; genlib.FITYEAR=Y
R=lambda tag: os.path.expanduser('~/rvt-research/rosetta')+'/%d_%s.rte'%(Y,tag)
S=scenes.Scene.__new__(scenes.Scene)
S.year=Y; S.g=rvtgen.Gen(sys.argv[1]); S.tr=scenes.trip(S.g); S.man={}; S.reg={}; S.counts={}; S.levels=[]; S.pkind={}; S.pname={}
base0=set(wledit.Editor(WL+'/'+scenes.SEEDF[Y]).m.ids)
gpv=rvtgen.Gen(R('params_wall_var'))
_w=[i for i in sorted(set(gpv.e.m.ids)-base0) if gpv.e.trace(i)[2]['class']=='SWall'][0]; _tw=gpv.template(_w); _LL={n:v for n,o,e,v in _tw['log']}
genlib2.PARAM_PTR={'int':int(re.search(r"'ptr': (\d+)",str(_LL['Element.m_pParamValueSetInt'])).group(1)),'str':int(re.search(r"'ptr': (\d+)",str(_LL['Element.m_pParamValueSetAString'])).group(1))}
S.PT=genlib2.ParamTpl(gpv,min(set(gpv.e.m.ids)-base0))
hb=rvtgen.Gen(R('house_base'))
tx=[int(l.split('\t')[1]) for l in open(os.path.expanduser('~/rvt-research/gt_geom/2024_house_base.tsv'),errors='replace') if l.startswith('EL') and l.split('\t')[2]=='TextNote'][0]
itag=hb.template(tx)['item'][16:18]
sys.path[:0]=[os.path.expanduser('~/rvt-research')]
import rvt_xcache, rvt_famparams as F
_have=set(F.captions(rvt_xcache.get_x_ro(sys.argv[1])['recs']).values())
NAMES=['C3X'+k for k in ('text','int','number','length','yesno')]
_dup=[n for n in NAMES if n in _have]
if _dup: sys.exit('REFUSED: parameter(s) %s already defined in the file (same name gives the same shared GUID: duplicate definition); nothing written'%_dup)
for k in ('text','int','number','length','yesno'): S.param(k,'C3X'+k)
g=S.g; known=set(g.e.m.ids)
# Latest registries (decoded from a Revit-made pair, c5xbind): (1) external-param table [count u32][guid16 + paramId u64]* sorted by guid,
# (2) binding map [count u32][categoryKey i64, n u32, bindingIds u64*]* sorted by key. Revit adds 24 B to (1) and one entry (or one id) to (2) per parameter.
_r=rvt_xcache.get_x_ro(sys.argv[1])['recs']; _cl=lambda c: sorted(k[0] if isinstance(k,tuple) else k for k,v in _r.items() if v['class']==c)
_pe0,_pb0=_cl('ParamElemExternal'),_cl('ParamBinding')
if not _pe0 or not _pb0: sys.exit('REFUSED: file has no existing shared parameter/binding to anchor the registries on; nothing written')
_PEGUID={a:_uuid.UUID(bytes_le=bytes.fromhex(str(_r[(a,'ParamElemExternal')]['fields']['m_externalParamKey']['m_guidValue']['m_guid']))).bytes_le for a in _pe0[:1]}
_newpe=[(a,_uuid.uuid5(_uuid.UUID('6f1c3a52-8d0e-4b7a-9c41-2e5d7b9a0f13'),'%s:%s'%(k,n)).bytes_le) for a,n,k in S.man['params']]
_newpb=[b for b,x in S.man['parts']]
def _reg_ops(raw):
    ops=[]
    # (1) guid table
    a0=_pe0[0]; pat=_PEGUID[a0]+struct.pack('<Q',a0); k=raw.find(pat); assert k>0 and raw.find(pat,k+1)<0, 'guid table anchor'
    ents=[]; q=k
    while q+24<=len(raw) and struct.unpack_from('<Q',raw,q+16)[0] in known: q+=24
    # walk back to the first entry
    q=k
    while struct.unpack_from('<Q',raw,q-8)[0] in known and q-24>4: q-=24
    n=struct.unpack_from('<I',raw,q-4)[0]; cur=[raw[q+24*i:q+24*i+24] for i in range(n)]; assert q+24*n<=len(raw) and pat in b''.join(cur), 'guid table parse'
    allr=sorted(cur+[g_+struct.pack('<Q',a) for a,g_ in _newpe]); ops.append((q-4,4+24*n,struct.pack('<I',len(allr))+b''.join(allr)))
    # (2) category map: find start q2 so that parsing [count]{key,n,ids} covers the anchor list of an existing binding
    anc=struct.pack('<Q',_pb0[0]); pos=raw.find(anc); assert pos>0
    for q2 in range(pos-6000,pos):
        if q2<4: continue
        c=struct.unpack_from('<I',raw,q2)[0]
        if not 1<=c<=200: continue
        o=q2+4; ok=True; ent=[]
        for _ in range(c):
            if o+12>len(raw): ok=False; break
            key=struct.unpack_from('<q',raw,o)[0]; m=struct.unpack_from('<I',raw,o+8)[0]
            if not(-3000000<key<-2000000 and 1<=m<=500 and o+12+8*m<=len(raw)): ok=False; break
            ids=struct.unpack_from('<%dQ'%m,raw,o+12)
            if not all(i in known for i in ids): ok=False; break
            ent.append((key,list(ids))); o+=12+8*m
        if ok and q2<pos<o and _pb0[0] in [i for kk,ii in ent for i in ii] and [e[0] for e in ent]==sorted(e[0] for e in ent): break
    else: raise AssertionError('category map not found')
    cat=-(2**64-_CATID) if False else struct.unpack('<q',_CATID.to_bytes(8,'little'))[0]
    d=dict(ent)
    d[cat]=sorted(d.get(cat,[])+_newpb)
    out=struct.pack('<I',len(d))+b''.join(struct.pack('<qI',kk,len(d[kk]))+b''.join(struct.pack('<Q',i) for i in d[kk]) for kk in sorted(d))
    ops.append((q2,o-q2,out))
    if os.environ.get('RVTGEN_DEBUG'): print('REGOPS', [(a,b,len(c)) for a,b,c in ops], 'guidtable n',n,'catmap count',c,'cats',sorted(d)[:5], file=sys.stderr)
    return ops
_CATID=(1<<64)-2000011
g.latest_edits=[('Latest',lambda raw: genlib2.apply_ops(raw,_reg_ops(raw)))]
g.itag=itag; g.commit(sys.argv[2]); print('wrote',S.counts)
