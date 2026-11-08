"""param-only add on an ARBITRARY 2024 project (experiment; Autodesk samples only): usage gen.py SEED OUT"""
import sys,os,re,struct,json
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
import cfb as _cfb
if len(sys.argv) != 3: sys.exit('usage: rvt_param_add_gen.py SEED OUT')
if os.path.realpath(sys.argv[1]) == os.path.realpath(sys.argv[2]): sys.exit('REFUSED: output path equals the input file; nothing written')
try: _fy = int(re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(sys.argv[1], 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file; nothing written')
if _fy != 2024: sys.exit('REFUSED: parameter add is only built for Revit 2024 files (this file is %d); nothing written' % _fy)
WL=os.path.expanduser('~/rvt-research/write-lab'); sys.path.insert(0,WL)
import rvtgen,genlib,genlib2,wledit,scenes
Y=2024; genlib2.YEAR=Y; genlib.FITYEAR=Y
R=lambda tag: os.path.expanduser('~/rvt-research/rosetta')+'/%d_%s.rte'%(Y,tag)
S=scenes.Scene.__new__(scenes.Scene)
S.year=Y; S.g=rvtgen.Gen(sys.argv[1]); S.tr=scenes.trip(S.g); S.man={}; S.reg={}; S.counts={}; S.levels=[]; S.pkind={}; S.pname={}
base0=set(wledit.Editor(WL+'/'+scenes.SEEDF[Y]).m.ids)
gpv=rvtgen.Gen(R('params_wall_var'))
_w=[i for i in sorted(set(gpv.e.m.ids)-base0) if gpv.e.trace(i)[2]['class']=='SWall'][0]; _tw=gpv.template(_w); _LL={n:v for n,o,e,v in _tw['log']}
genlib2.PARAM_PTR={'int':int(re.search(r"'ptr': (\d+)",str(_LL['Element.m_pParamValueSetInt'])).group(1)),'str':int(re.search(r"'ptr': (\d+)",str(_LL['Element.m_pParamValueSetAString'])).group(1))}
S.PT=genlib2.ParamTpl(gpv,min(set(gpv.e.m.ids)-base0))
hb=rvtgen.Gen(R('house_base'))
tx=[int(l.split('\t')[1]) for l in open(os.path.expanduser('~/rvt-research/gt_geom/2024_house_base.tsv'),errors='replace') if l.startswith('EL') and l.split('\t')[2]=='TextNote'][0]
itag=hb.template(tx)['item'][16:18]
sys.path[:0]=[os.path.expanduser('~/rvt-research')]
import rvt_xcache, rvt_famparams as F
_have=set(F.captions(rvt_xcache.get_x_ro(sys.argv[1])['recs']).values())
NAMES=['C3X'+k for k in ('text','int','number','length','yesno')]
_dup=[n for n in NAMES if n in _have]
if _dup: sys.exit('REFUSED: parameter(s) %s already defined in the file (same name gives the same shared GUID: duplicate definition); nothing written'%_dup)
for k in ('text','int','number','length','yesno'): S.param(k,'C3X'+k)
g=S.g; known=set(g.e.m.ids)
g.latest_edits=[('Latest',lambda raw: genlib2.apply_ops(raw,genlib2.registry_update(raw,{},known)))]
g.itag=itag; g.commit(sys.argv[2]); print('wrote',S.counts)
