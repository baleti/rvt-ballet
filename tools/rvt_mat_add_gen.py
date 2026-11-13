"""material create on an ARBITRARY 2024 project (experiment; Autodesk samples only): usage gen.py SEED OUT NAME
Clones the Revit-made empty MaterialElem (c5xmat pair: name only, no assets), new id, new name; appends the id to the Latest id-list(s) holding existing MaterialElem ids."""
import sys,os,re,struct
os.environ.setdefault('RVTGEN_INPLACE','1')      # insert into the existing member (Revit's own way); the default append path produces CArchiveException 105 on Structural 2024
if len(sys.argv) != 4: sys.exit('usage: rvt_mat_add_gen.py SEED OUT NAME')
if os.path.realpath(sys.argv[1]) == os.path.realpath(sys.argv[2]): sys.exit('REFUSED: output path equals the input file; nothing written')
WL=os.path.expanduser('~/rvt-research/write-lab'); sys.path.insert(0,WL); sys.path.insert(1,os.path.expanduser('~/rvt-research'))
import cfb as _cfb
try: _fy=int(re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(sys.argv[1],'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le','ignore')).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file; nothing written')
if _fy != 2024: sys.exit('REFUSED: material create is only built for Revit 2024 files (this file is %d); nothing written'%_fy)
NAME=sys.argv[3]
if not NAME or len(NAME)>200 or any(c in NAME for c in '{}[]|;<>?`~\\:') : sys.exit('REFUSED: invalid material name (empty, too long or contains Revit-forbidden characters); nothing written')
import rvtgen,genlib,genlib2,rvt_xcache
TPL=os.path.expanduser('~/c2x-diff/c5xmat/after.rvt')
if not os.path.exists(TPL): sys.exit('REFUSED: template pair ~/c2x-diff/c5xmat/after.rvt missing')
recs=rvt_xcache.get_x_ro(sys.argv[1])['recs']
mats=sorted(k[0] if isinstance(k,tuple) else k for k,v in recs.items() if v['class']=='MaterialElem')
for k,v in recs.items():
    if v['class']=='MaterialElem':
        try:
            nm=v['fields']['m_pMaterial']['obj']['m_name']
            if nm==NAME: sys.exit('REFUSED: a material named %r already exists; nothing written'%NAME)
        except (KeyError,TypeError): pass
if not mats: sys.exit('REFUSED: no existing MaterialElem to anchor the Latest id-list; nothing written')
g=rvtgen.Gen(sys.argv[1]); known=set(g.e.m.ids)
T=rvtgen.Gen(TPL).template(1542978)
nid=g.nextid; g.nextid+=1
import scenes
tr=scenes.trip(g)
hd,rec,it,_,row=genlib2.make_symbol_copy(g,T,nid)
L={n:(o,e) for n,o,e,v in T['log']}; o,e=L['Material.m_name']
rec=bytearray(rec); rec[o:e]=genlib.ustr(NAME); rec=g.stamp(bytes(rec))
r=bytearray(row); struct.pack_into('<3I',r,8,*tr)
g.new.append((hd,rec,it,nid)); g.rows.append(bytes(r))
grp={mats[0]:[nid]}
g.latest_edits=[('Latest',lambda raw: genlib2.apply_ops(raw,genlib2.registry_update(raw,grp,known)))]
g.commit(sys.argv[2]); print('wrote material',nid,NAME)
