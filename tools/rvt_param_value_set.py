"""set a STRING value of a (new) shared parameter on an existing element that already has a string value set (experiment, Autodesk samples only):
usage rvt_param_value_set.py SRC OUT EID PARAM_NAME VALUE   (inserts [pid u64][nchars u32][utf16] into ParamValueSetAString in signed pid order, bumps the count)"""
import sys,os,struct
if len(sys.argv)!=6: sys.exit(__doc__)
src,out,eid,pname,val=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4],sys.argv[5]
if os.path.realpath(src)==os.path.realpath(out): sys.exit('REFUSED: output path equals the input file; nothing written')
for p in ('~/rvt-research/edit-lab','~/rvt-research/write-lab','~/rvt-research'): sys.path.insert(0,os.path.expanduser(p))
os.environ.setdefault('RVT_GEOM','1')
import rvtedit, rvt_xcache
if any(ord(c)>0xFFFF or ord(c)<32 for c in val): sys.exit('REFUSED: unsupported characters in value; nothing written')
recs=rvt_xcache.get_x_ro(src)['recs']
pids=[k[0] for k,v in recs.items() if v['class']=='ParamElemExternal' and (v['fields'].get('m_pParamDef') or {}).get('obj',{}).get('m_caption')==pname]
if len(pids)!=1: sys.exit('REFUSED: parameter %r found %d times; nothing written'%(pname,len(pids)))
pid=pids[0]
ed=rvtedit.Edit(src); log=ed.g.e.trace(eid)[3]
L={l[1]:l for l in log}
if 'ParamValueSetAString.m_paramSet' not in L: sys.exit('REFUSED: element %d has no string value set to extend; nothing written'%eid)
a,b=L['ParamValueSetAString.m_paramSet'][2],L['ParamValueSetAString.m_paramSet'][3]
raw=bytes(ed.g.bj[a:b]); n=struct.unpack_from('<I',raw,0)[0]; o=4; ents=[]
for _ in range(n):
    k=struct.unpack_from('<Q',raw,o)[0]; m=struct.unpack_from('<I',raw,o+8)[0]; ents.append((k,raw[o:o+12+2*m])); o+=12+2*m
if o!=len(raw): sys.exit('REFUSED: string value set did not parse (%d != %d); nothing written'%(o,len(raw)))
sg=lambda k: k-(1<<64) if k>=1<<63 else k
if any(k==pid for k,_ in ents): sys.exit('REFUSED: parameter already has a value on this element; use set-by-pid; nothing written')
ents.append((pid,struct.pack('<QI',pid,len(val))+val.encode('utf-16-le'))); ents.sort(key=lambda t:sg(t[0]))
new=struct.pack('<I',len(ents))+b''.join(e for _,e in ents)
ed._rec_edit(eid,[(a,b-a,new)]); ed.save(out); print('wrote',out,'pid',pid,'on',eid)
