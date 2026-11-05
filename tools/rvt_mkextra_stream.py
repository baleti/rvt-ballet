"""mkextra.py SRC.rvt DST.rvt: synthetic CFB with one extra unknown stream (ZZ_UnknownStream, 4 KB random payload) added to an Autodesk sample; for save-gate read-write-gap tests."""
import sys,os,struct,copy
sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab')); import cfb
src,dst=sys.argv[1:3]
c=cfb.CFB(open(src,'rb').read())
root=c.entries[0]
tmpl=[e for e in c.entries if e.type==2][0]
n=cfb.Entry()
for k in cfb.Entry.__slots__:
    if k!='raw' and hasattr(tmpl,k): setattr(n,k,getattr(tmpl,k))
name='ZZ_UnknownStream'; nb=name.encode('utf-16le')+b'\0\0'
raw=bytearray(tmpl.raw); raw[0:64]=nb.ljust(64,b'\0'); struct.pack_into('<H',raw,64,len(nb))
struct.pack_into('<III',raw,68,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF)
n.raw=bytes(raw); n.idx=len(c.entries); n.name=name; n.left=n.right=n.child=0xFFFFFFFF
n.data=os.urandom(1000)+b'\x00\xff'*3000; n.size=len(n.data)
# attach as right of the rightmost node of root's tree
cur=c.entries[root.child]
while cur.right!=0xFFFFFFFF: cur=c.entries[cur.right]
cur.right=n.idx; r=bytearray(cur.raw); struct.pack_into('<I',r,72,n.idx); cur.raw=bytes(r)
c.entries.append(n)
cfb.write(c,dst)
d=cfb.CFB(open(dst,'rb').read()).streams()
print('extra stream present:',name in d,len(d),'streams; payload sha',__import__('hashlib').sha256(n.data).hexdigest()[:10])
