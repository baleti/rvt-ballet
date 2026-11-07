"""rvt-ballet ADD (clone-and-patch): clone an existing FamilyInstance (--src) in a project, new id, moved by dx,dy,dz; Latest id-lists containing src get the new id.
Text notes etc: pass --nolatest."""
import sys,struct,os,argparse; sys.path.insert(0,'~/rvt-research/write-lab'); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
os.environ['RVT_GEOM']='1'
import rvtgen,genlib
import rvt_idlist as idlist
ap=argparse.ArgumentParser(); ap.add_argument('seed'); ap.add_argument('out'); ap.add_argument('--src',type=int,required=True)
ap.add_argument('--dx',type=float,default=3.0); ap.add_argument('--dy',type=float,default=4.0); ap.add_argument('--dz',type=float,default=0.0); ap.add_argument('--nolatest',action='store_true'); ap.add_argument('--force',action='store_true',help='skip the dependents screen (instances that own children corrupt the model when copied)')
a=ap.parse_args()
if not a.force:
    sys.path.insert(0,os.path.expanduser('~/rvt-research/edit-lab')); sys.path.insert(0,os.path.expanduser('~/rvt-research'))
    import rvtedit
    _deps=rvtedit.Edit(a.seed).dependents(a.src)
    if _deps: sys.exit('REFUSED: source %d owns %d dependent element(s) %s (header deletion lists name it); copying it corrupts the model. Pick a childless source or --force.'%(a.src,len(_deps),_deps[:6]))
    print('dependents screen: none')
g=rvtgen.Gen(a.seed); W=g.W; S=a.src; T=g.template(S); idS=struct.pack(g.IDF,S)
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
        out,Ls=idlist.add_to_lists(raw,S,nid); print('latest lists',[(l[2]) for l in Ls]); assert Ls,'no id-list found'; return out
    g.latest_edits=[('Latest',reg)]
g.itag=T['item'][W+8:W+10]
g.commit(a.out); print('ok',a.out,'new id',nid)
