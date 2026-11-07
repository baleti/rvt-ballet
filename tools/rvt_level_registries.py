"""Locate Level registries in Global/Latest of a .rvt/.rte (any year): for each Level, count occurrences of its 8-byte id in the decompressed Latest stream, and report the registry shape of the lowest level. usage: lvreg.py FILE..."""
import sys,os,struct,zlib,re; sys.path.insert(0,'~/rvt-research/write-lab'); os.environ['RVT_GEOM']='1'
import wledit,rvtw,rvtgen
for f in sys.argv[1:]:
    tag=os.path.basename(f)[:28]
    try:
        sys.path.insert(0,'~/rvt-research'); import rvt_geometry as G, cfb as C
        ix=G.file_geometry_index(f); lv=sorted(e for e,v in ix.items() if str(v)=='Level')
        c=C.CFB(open(f,'rb').read()) if hasattr(C,'CFB') else None
        P=rvtw.Stream(c.streams()['Global/Latest'].data).payload; k=P.find(rvtw.GZ)
        raw=zlib.decompressobj(-15).decompress(P[k+10:])
        res=[]
        for i in lv:
            b=struct.pack('<Q',i); pos=[m.start() for m in re.finditer(re.escape(b),raw)]
            res.append((i,len(pos)))
        # registry shape: occurrences of lowest id preceded by a count byte
        print(tag,'levels',len(lv),'occ(id,n)',res[:6],flush=True)
    except Exception as ex: print(tag,'ERR',type(ex).__name__,str(ex)[:80],flush=True)
