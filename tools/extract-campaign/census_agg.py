"""per-year flat/nested open-check table for one census. usage: CAMPAIGN_ROOT=DIR python3 census_agg.py [--json]"""
import json,os,glob,collections,sys
R = os.environ.get('CAMPAIGN_R', os.getcwd())          # working directory of the campaign (lists, lift output, chk results); keep it outside the repos
lines=[l.rstrip('\n').split('\t') for l in open(R+'/census3.list')]
year={('c%s'%l[0]):l[1] for l in lines}
info={}  # staged name -> (year, category, nested, depth)
for c in os.listdir(R+'/lift3'):
    mp=os.path.join(R,'lift3',c,'manifest.json')
    if not os.path.exists(mp): continue
    m=json.load(open(mp))
    for f in m['families']:
        r=f.get('rfa') or {}
        if r.get('file'):
            key='%s__%s'%(c,r['file'][len('families/'):].replace('/','__'))
            info[key]=(year.get(c,'?'),f.get('category'),bool(r.get('nested')),r.get('nested_depth') or 0)
res={}
for fn in glob.glob(R+'/chk/res_c3_*/rfacheck.tsv'):
    for l in open(fn):
        p=l.rstrip('\n').split('\t')
        if p[0] in('OPEN','OPENFAIL'): res[p[1]]=p[0]
tab=collections.defaultdict(lambda:[0,0]); tot=[0,0]; unk=0; bad=[]
for name,st in res.items():
    i=info.get(name)
    if not i: unk+=1; continue
    y,cat,nest,dep=i; k=(y,'nested' if nest else 'flat')
    tab[k][0 if st=='OPEN' else 1]+=1; tot[0 if st=='OPEN' else 1]+=1
    if st=='OPENFAIL': bad.append((y,cat,dep,name))
print('checked',len(res),'of',len(info),'| OPEN',tot[0],'OPENFAIL',tot[1],'unmatched',unk)
for k in sorted(tab): print(' ',k,'open',tab[k][0],'fail',tab[k][1])
bycat=collections.defaultdict(lambda:[0,0])
for name,st in res.items():
    i=info.get(name)
    if i: bycat[(i[1],'nested' if i[2] else 'flat')][0 if st=='OPEN' else 1]+=1
fails=sorted(((v[1],k) for k,v in bycat.items() if v[1]),reverse=True)[:15]
print('categories with failures:',fails)
for b in bad[:15]: print('FAIL',b)
if '--json' in sys.argv: json.dump({'tab':{'%s|%s'%k:v for k,v in tab.items()},'bad':bad},open(R+'/census3_agg.json','w'))
