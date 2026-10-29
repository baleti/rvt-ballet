"""tagscan.py DIR OUT.json : per-.rfa histogram of record class tags (needs olefile, rvtx from $RVT_EXTRACT, rvt2text from $RVT_RESEARCH)"""
import sys,os,glob,struct,collections,json
for p in (os.environ.get('RVT_EXTRACT'), os.environ.get('RVT_RESEARCH')):
    if p: sys.path.insert(0, p)
import rvtx, olefile, rvt2text as T
from rvtx import partition as PT
out={}
for f in sorted(glob.glob(sys.argv[1]+'/**/*.rfa',recursive=True)):
    try:
        o=olefile.OleFileIO(f); pn=[y for y in ['/'.join(e) for e in o.listdir(streams=True)] if y.startswith('Partitions/')][0]
        d=PT.parse_joined(T.joined(o.openstream(pn).read()),8)
        c=collections.Counter()
        for doc in d:
            for ch in 'HRZ':
                for x in doc[ch]:
                    if x[0]!=(1<<64)-1: c[struct.unpack_from('<H',x[1],0)[0]]+=1
        out[os.path.relpath(f,sys.argv[1]).replace('/','__')]={'n':len(d),'tags':dict(c)}
    except Exception as e: out[f]={'err':str(e)}
json.dump(out,open(sys.argv[2],'w'))
