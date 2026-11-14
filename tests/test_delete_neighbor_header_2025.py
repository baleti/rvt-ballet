"""c5x-rvtread items 82/87/89 (REVISED: it was a reader blind spot, not an over-cut): deleting AssemblyCodeTable 1301875 (Snowdon HVAC 2025) cuts 125367 bytes although the record spans 125232: the extra 135 bytes are the ElementHeader of the NEXT record (ParamElemFamily 41612), which then reads back with no header. The edit layer accepts the delete (class is in DELETE_VM_VERIFIED from a 2024 scene); the read-back gate must refuse it (never accept a delete that damages a surviving element). Skips when the local 2025 sample is absent."""
import os, sys, tempfile, shutil
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKUPS'] = _T + '/b'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2025/48_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    ops = [edit.validate_op({'op': 'delete', 'eid': 1301875})]
    try: nb, dl = edit.apply_full(d.buf, ops)
    except edit.EditError as e: print('OK refused by the edit layer:', str(e)[:100]); sys.exit(0)
    save._readback(d.buf, nb, ops)      # must NOT raise any more: the 'survivor 41612 lost its ElementHeader' refusal was a reader blind spot (first record of a partition, id at offset 0), fixed in rvt-core bf9d25e + rvt-research 2ed204c; a regression of the scanner brings the refusal back
    print('OK accepted: the survivor header is readable (Revit 2025 VM open of this output: queue item 86)')
finally: shutil.rmtree(_T, ignore_errors=True)
