"""Aggregate a family-extraction campaign (census lists + lift output + Revit open checks): year x category-group x depth, opened/total, failure classes, lift errors.
Aggregate only (no client names/paths). usage: CAMPAIGN_ROOT=DIR python3 campaign_agg.py [--write]
Inputs under DIR: census3.list/census4.list (id<TAB>year per project), lift3/ lift4/ (rvt-extract output with manifest.json), lift3.summary, chk/res_c3_*/rfacheck.tsv"""
import json,os,glob,collections,sys,re
R = os.environ.get('CAMPAIGN_R', os.getcwd())          # working directory of the campaign (lists, lift output, chk results); keep it outside the repos
CENSUS=[('c3','lift3','census3.list'),('c4','lift4','census4.list')]
info={}; lifterr=collections.Counter(); projs=collections.Counter(); skipped=collections.Counter()
for tag,ld,lst in CENSUS:
    if not os.path.exists(f'{R}/{lst}'): continue
    year={'c%s'%l.split('\t')[0]:l.split('\t')[1] for l in open(f'{R}/{lst}')}
    summ=f'{R}/{ld}.summary'
    if os.path.exists(summ):
        for l in open(summ):
            m=re.match(r'c(\d+) (\d+) \d+ rc=(\d+)',l)
            if m: projs[(tag,m.group(2),'rc=%s'%m.group(3))]+=1
    for c in (os.listdir(f'{R}/{ld}') if os.path.isdir(f'{R}/{ld}') else []):
        mp=f'{R}/{ld}/{c}/manifest.json'
        if not os.path.exists(mp): continue
        for f in json.load(open(mp))['families']:
            r=f.get('rfa') or {}
            y=year.get(c,'?')
            if r.get('file'):
                info[f'{tag}:{c}__'+r['file'][len('families/'):].replace('/','__')]=(y,f.get('category') or '?',r.get('nested_depth') or 0)
            else:
                skipped[(y,('error: '+str(r.get('error'))[:60]) if r.get('status')=='error' else ('in-place family (no standalone rfa)' if f.get('in_place') else 'system/loadable without rfa (e.g. mullions, panels)'))]+=1
res={}
for tag,ld,lst in CENSUS:
    for fn in glob.glob(f'{R}/chk/res_{tag}_*/rfacheck.tsv'):
        for l in open(fn):
            p=l.rstrip('\n').split('\t')
            if p[0] in('OPEN','OPENFAIL'): res[f'{tag}:{p[1]}']=(p[0],p[2] if p[0]=='OPENFAIL' and len(p)>2 else '')
tab=collections.defaultdict(lambda:[0,0,0]); fc=collections.Counter()
for k,i in info.items():
    y,cat,d=i; dk='d0' if d==0 else ('d1' if d==1 else 'd2+')
    t=tab[(y,dk)]; t[2]+=1
    st=res.get(k)
    if st:
        if st[0]=='OPEN': t[0]+=1
        else: t[1]+=1; fc[(y,dk,re.sub(r'\d+','N',st[1])[:90])]+=1
out=['# Family extraction campaign (aggregate, no client data)','',
 f'extracted .rfa: {len(info)}; open-checked: {len(res)} (OPEN {sum(1 for v in res.values() if v[0]=="OPEN")}, OPENFAIL {sum(1 for v in res.values() if v[0]!="OPEN")})','',
 '## Opened / checked / extracted by Revit year x nesting depth (Revit 2024 open check)','','| year | depth | opened | failed | not yet checked | extracted |','|---|---|---|---|---|---|']
for (y,d),(o,f,t) in sorted(tab.items()): out.append(f'| {y} | {d} | {o} | {f} | {t-o-f} | {t} |')
out+=['','## Failure classes (ranked)','']
for (y,d,m),n in fc.most_common(): out.append(f'- {n} x {y} {d}: {m}')
out+=['','## Projects lifted (rc) ','']
for k,n in sorted(projs.items()): out.append(f'- {k}: {n}')
out+=['','## Families not written (reason, year)','']
for k,n in skipped.most_common(15): out.append(f'- {n} x {k}')
s='\n'.join(out)+'\n'
print(s)
if '--write' in sys.argv: open(R+'/CAMPAIGN.md','w').write(s)
