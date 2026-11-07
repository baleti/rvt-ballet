import sys,os,struct,zlib,re; sys.path.insert(0,'~/rvt-research/write-lab'); sys.path.insert(0,'~/rvt-research')
import rvtw, rvt_geometry as G, cfb as C
f=sys.argv[1]; ix=G.file_geometry_index(f); lv=sorted(e for e,v in ix.items() if str(v)=='Level')
c=C.CFB(open(f,'rb').read()); st=c.streams()
P=rvtw.Stream(st['Global/Latest'].data).payload; k=P.find(rvtw.GZ); raw=zlib.decompressobj(-15).decompress(P[k+10:])
i=int(sys.argv[2]); b=struct.pack('<I',i)
for m in re.finditer(re.escape(b),raw):
    p=m.start(); print(p, raw[p-12:p].hex(),'|',raw[p:p+36].hex())
