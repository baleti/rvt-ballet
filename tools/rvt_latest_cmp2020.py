import sys,os,struct,zlib,re; sys.path.insert(0,'~/rvt-research/write-lab'); os.environ['RVT_GEOM']='1'
import rvtw, cfb as C
def latest(f):
    c=C.CFB(open(f,'rb').read()); P=rvtw.Stream(c.streams()['Global/Latest'].data).payload; k=P.find(rvtw.GZ); return zlib.decompressobj(-15).decompress(P[k+10:])
A=latest('lv_A.rvt'); B=latest('lv_B.rvt'); W=4; nid=1474096; idb=struct.pack('<I',nid)
low=struct.pack('<I',417275)
occ=[m.start() for m in re.finditer(re.escape(low),A)]; print(occ, len(occ))
cnt=[A[o-4] for o in occ]; print('cnt byte before id',cnt)
E_=idb+struct.pack('<I',1)+struct.pack('<2d',9.0,9.0)
s=occ; cn=[struct.unpack_from('<I',A,o-4)[0] for o in occ]; print('cnt u32',cn)
ins=[(s[0]+cn[0]*W,idb),(s[2]-8,idb+bytes(4)),(s[2]+cn[2]*W,idb),(s[4]-4,E_),(s[5]-4,E_),(s[6]-4,E_),(s[6]+cn[6]*(W+20),E_)]
out=bytearray(A)
edits=[(o-4,('c',)) for o in occ]+[(p,('i',b)) for p,b in ins]
for p,k in sorted(edits,key=lambda x:-x[0]):
    if k[0]=='c': out[p]+=1
    else: out[p:p]=k[1]
print(len(A),len(out),len(B))
d=[i for i in range(min(len(out),len(B))) if out[i]!=B[i]]; print('diff bytes',len(d),d[:20])
