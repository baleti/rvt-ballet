"""KIND (optional 6th arg, default string): string | double | int | eid. double/int/eid insert a fixed-size entry [f64 value][pid u64] (double, as written by Revit) | [pid u64][i32] (int, layout from existing sets, NOT Revit-verified) into the element's ParamValueSetDouble/Int/ElementId (sorted by signed pid, count bumped); refused unless that set object already exists on the element (a null set pointer would need a new object, not built) and the parameter definition type matches (double: has m_specTypeId; int: has m_lowBound).
set a STRING value of a (new) shared parameter on an existing element that already has a string value set (experiment, Autodesk samples only):
usage rvt_param_value_set.py SRC OUT EID PARAM_NAME VALUE   (inserts [pid u64][nchars u32][utf16] into ParamValueSetAString in signed pid order, bumps the count)"""
import sys,os,struct
if len(sys.argv) not in (6,7): sys.exit(__doc__)
src,out,eid,pname,val=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4],sys.argv[5]
kind=sys.argv[6] if len(sys.argv)==7 else 'string'
if kind not in ('string','double','int','yesno','eid'): sys.exit('REFUSED: unknown kind')
if os.path.realpath(src)==os.path.realpath(out): sys.exit('REFUSED: output path equals the input file; nothing written')
import re as _re
sys.path.insert(0,os.path.expanduser('~/rvt-research/write-lab'))
import cfb as _cfb
try: _fy=int(_re.search(r'(20[12]\d)',bytes(_cfb.CFB(open(src,'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le','ignore')).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file; nothing written')
PTR={2024:{'text':672,'int':514,'double':680,'yesno':3002},2026:{'text':702,'int':542,'double':710,'yesno':3145}}   # definition class pointers per Revit year (read off Revit-made files)
if _fy not in PTR: sys.exit('REFUSED: parameter values are only built for Revit 2024/2026 files (this file is %d); nothing written'%_fy)
for p in ('~/rvt-research/edit-lab','~/rvt-research/write-lab','~/rvt-research'): sys.path.insert(0,os.path.expanduser(p))
os.environ.setdefault('RVT_GEOM','1')
import rvtedit, rvt_xcache
if kind=='string' and any(ord(c)>0xFFFF or ord(c)<32 for c in val): sys.exit('REFUSED: unsupported characters in value; nothing written')
recs=rvt_xcache.get_x_ro(src)['recs']
BUILTIN=pname.startswith('pid:')      # c1x-rvttype 2026-11-16: built-in parameter by signed pid (no ParamElemExternal exists); int/yesno only
if BUILTIN and kind not in ('int','yesno'): sys.exit('REFUSED: a built-in pid is only supported for int/yesno; nothing written')
pids=[int(pname[4:])%(1<<64)] if BUILTIN else [k[0] for k,v in recs.items() if v['class']=='ParamElemExternal' and (v['fields'].get('m_pParamDef') or {}).get('obj',{}).get('m_caption')==pname]
if len(pids)!=1: sys.exit('REFUSED: parameter %r found %d times; nothing written'%(pname,len(pids)))
pid=pids[0]
ed=rvtedit.Edit(src); log=ed.g.e.trace(eid)[3]
L={l[1]:l for l in log}
SETS={'string':'ParamValueSetAString.m_paramSet','double':'ParamValueSetDouble.m_paramSet','int':'ParamValueSetInt.m_paramSet','eid':'ParamValueSetElementId.m_paramSet'}
if kind!='string' and BUILTIN:
    if kind=='yesno' and val not in ('0','1'): sys.exit('REFUSED: value not 0/1; nothing written')
    kind='int'
    try: pk=struct.pack('<i',int(val))
    except ValueError: sys.exit('REFUSED: value does not parse; nothing written')
elif kind!='string':
    d=(recs[(pid,'ParamElemExternal')] if (pid,'ParamElemExternal') in recs else [v for k,v in recs.items() if (k[0] if isinstance(k,tuple) else k)==pid][0])['fields']['m_pParamDef']['obj']
    _pt=(recs[(pid,'ParamElemExternal')] if (pid,'ParamElemExternal') in recs else [v for k,v in recs.items() if (k[0] if isinstance(k,tuple) else k)==pid][0])['fields']['m_pParamDef']['ptr']   # definition class pointer encodes the data type (Revit-made files: 672 text, 514 int, 680 double, 3002 yes/no, 2916 material)
    if kind=='yesno' and (_pt!=PTR[_fy]['yesno'] or val not in ('0','1')): sys.exit('REFUSED: not a Yes/No parameter or value not 0/1; nothing written')
    if kind=='yesno': kind='int'
    elif kind=='int' and _pt!=PTR[_fy]['int']: sys.exit('REFUSED: parameter definition is not an Integer type; nothing written')
    if kind=='double' and (_pt!=PTR[_fy]['double'] or 'm_specTypeId' not in d): sys.exit('REFUSED: parameter definition is not a Double type; nothing written')
    if kind=='eid': sys.exit('REFUSED: element-id parameter values not verified; nothing written')
    FS={'double':16,'int':12}[kind]
    try: pk=struct.pack('<d',float(val)) if kind=='double' else struct.pack('<i',int(val))
    except ValueError: sys.exit('REFUSED: value does not parse; nothing written')
if kind=='int' and SETS[kind] not in L:
    # element has a null Int set pointer: Revit (paired experiment c5xpi) turns the 4-byte null into the 6-byte class pointer ffffffff+tag and appends a new ParamValueSetInt object right after the Double set object
    ptr=L.get('Element.m_pParamValueSetInt'); dbl=L.get('ParamValueSetDouble.m_paramSet')
    if not ptr or ptr[3]-ptr[2]!=4 or bytes(ed.g.bj[ptr[2]:ptr[3]])!=b'\0\0\0\0' or not (dbl or L.get('CellList.m_cells')): sys.exit('REFUSED: element %d has no int set and no known place to create one; nothing written'%eid)
    tag=None
    for k2,v2 in recs.items():
        e2=k2[0] if isinstance(k2,tuple) else k2
        try: l2={l[1]:l for l in ed.g.e.trace(e2)[3]}.get('Element.m_pParamValueSetInt')
        except Exception: continue
        if l2 and l2[3]-l2[2]==6: tag=bytes(ed.g.bj[l2[2]:l2[3]]); break
    if not tag: sys.exit('REFUSED: no element in the file carries an Int set pointer to copy the class tag from; nothing written')
    cl=L.get('CellList.m_cells'); at=cl[2] if cl and (not dbl or dbl[3]<=cl[2]) else dbl[3]      # Revit pair c1xyn8: the new set object sits right before CellList.m_cells (also when the Double set is null)
    ed._rec_edit(eid,[(ptr[2],4,tag),(at,0,struct.pack('<IQi',1,pid,int(val)))]); ed.save(out); print('wrote',out,'pid',pid,'on',eid,'int (new set object)'); sys.exit(0)
if SETS[kind] not in L: sys.exit('REFUSED: element %d has no %s value set object to extend; nothing written'%(eid,kind))
a,b=L[SETS[kind]][2],L[SETS[kind]][3]
raw=bytes(ed.g.bj[a:b]); n=struct.unpack_from('<I',raw,0)[0]; o=4; ents=[]
for _ in range(n):
    k=struct.unpack_from('<Q',raw,o+8 if kind=='double' else o)[0]
    sz=12+2*struct.unpack_from('<I',raw,o+8)[0] if kind=='string' else FS
    ents.append((k,raw[o:o+sz])); o+=sz
if o!=len(raw): sys.exit('REFUSED: value set did not parse (%d != %d); nothing written'%(o,len(raw)))
sg=lambda k: k-(1<<64) if k>=1<<63 else k
if any(k==pid for k,_ in ents): sys.exit('REFUSED: parameter already has a value on this element; use set-by-pid; nothing written')
if [sg(k) for k,_ in ents]!=sorted(sg(k) for k,_ in ents): sys.exit('REFUSED: existing set not in signed pid order; nothing written')
ents.append((pid,(struct.pack('<QI',pid,len(val))+val.encode('utf-16-le')) if kind=='string' else (pk+struct.pack('<Q',pid) if kind=='double' else struct.pack('<Q',pid)+pk))); ents.sort(key=lambda t:sg(t[0]))
new=struct.pack('<I',len(ents))+b''.join(e for _,e in ents)
ed._rec_edit(eid,[(a,b-a,new)]); ed.save(out); print('wrote',out,'pid',pid,'on',eid,kind)
