import struct
def find_lists(a,src,maxn=200000,w=8):
    """occurrences of src id (u64) inside an ascending u64 id-list preceded by u32 count n: return [(count_pos,list_start,n,idx)]"""
    F='<I' if w==4 else '<Q'; b=struct.pack(F,src); out=[]; j=-1
    while True:
        j=a.find(b,j+1)
        if j<0: break
        # src may be at index idx of list; walk back while ascending ids and check count
        for idx in range(0,64):
            s=j-w*idx
            if s-4<0: break
            n=struct.unpack_from('<I',a,s-4)[0]
            if n>idx and 2<=n<maxn and s+w*n<=len(a):
                ids=struct.unpack_from('<%d%s'%(n,F[1]),a,s)
                if all(ids[k]<ids[k+1] for k in range(n-1)) and ids[idx]==src and ids[-1]<(1<<40) and ids[0]>0:
                    out.append((s-4,s,n,idx)); break
    return out
def add_to_lists(a,src,newid,w=8):
    F='<I' if w==4 else '<Q'; L=find_lists(a,src,w=w); out=bytearray(a)
    for cp,s,n,idx in sorted(L,reverse=True):
        # new id is larger than all existing
        assert newid>struct.unpack_from(F,a,s+w*(n-1))[0]
        out[s+w*n:s+w*n]=struct.pack(F,newid); out[cp:cp+4]=struct.pack('<I',n+1)
    return bytes(out),L
