"""The id-0 element bucket (reader ghost decodes that flip when nearby bytes change; real file f31 refused every edit on it) is declared modified ONLY when the byte-level bounds
(dirty_members and member_span_max) are in the manifest; otherwise an el:0 change stays an undeclared difference. RVTBALLET_BUCKET0=0 switches it off."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path[:0] = [os.path.expanduser('~/src/savegate'), HERE]
from rvtballet import save
bounded = {'modified': ['el:5'], 'dirty_members': {'Partitions/0': [3]}, 'member_span_max': 2048}
assert 'el:0' in save._declare_bucket0(dict(bounded, modified=['el:5']))['modified']
assert 'el:5' in save._declare_bucket0(dict(bounded, modified=['el:5']))['modified']
assert 'el:0' not in save._declare_bucket0({'modified': ['el:5']})['modified'], 'no bounds, no declaration'
assert 'el:0' not in save._declare_bucket0({'modified': ['el:5'], 'dirty_members': {'Partitions/0': [3]}})['modified'], 'no span bound'
os.environ['RVTBALLET_BUCKET0'] = '0'
assert 'el:0' not in save._declare_bucket0(dict(bounded, modified=['el:5']))['modified']
print('bucket0 declaration OK')
