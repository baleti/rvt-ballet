import olefile
S='~/rvtsave-work/c1x_keep/s24_43_Snowdon_Towers_Sample_Structural.rvt'; O='~/c2x-rm/keep66/chain_last.rvt'
def slack(p):
    o=olefile.OleFileIO(p); ss=o.sectorsize; d=open(p,'rb').read(); r={}
    for e in o.direntries:
        if e is None or e.entry_type!=2 or e.size<o.minisectorcutoff: continue
        s=e.isectStart; chain=[]
        while s<0xFFFFFFF0 and len(chain)<10**6: chain.append(s); s=o.fat[s]
        used=e.size; tot=len(chain)*ss
        lastsec=chain[(used-1)//ss]; start=(lastsec+1)*ss+((used-1)%ss)+1-ss+ss
        # bytes after logical end in last needed sector
        endoff=(lastsec+1)*ss + (used-1)%ss + 1 - 0
        r[e.name]=(endoff, ss-((used-1)%ss+1), len(chain)-((used+ss-1)//ss), d)
    return r
a=slack(S); b=slack(O)
for n in a:
    if n in b:
        (s1,l1,x1,d1),(s2,l2,x2,d2)=a[n],b[n]
        print(n,'size-diff chain extra sectors',x1,x2,'tail slack',l1,l2,'same',d1[s1:s1+l1]==d2[s2:s2+l2],'nonzero src',any(d1[s1:s1+l1]))
