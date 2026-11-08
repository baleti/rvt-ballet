"""c1x-rvtdel item 51: singleton 'TrackingElement' classes (Plumbing 2026 ActiveGeoLocationTrackingElement was accepted in DELETE_ANY mode) match UNIQUE_CLASS; real classes do not."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
for c in ('ActiveGeoLocationTrackingElement', 'AutoJoinTracker', 'ProjectInfo'): assert edit.UNIQUE_CLASS.search(c), c
for c in ('SWall', 'Floor', 'FamilyInstance', 'TextNote', 'DimensionStyle'): assert not edit.UNIQUE_CLASS.search(c), c
print('OK')
