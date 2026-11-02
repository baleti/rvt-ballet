import os, tempfile
# pytest runs must not write pending-edit stores into the user's real data dir
os.environ.setdefault('RVTBALLET_EDITSTORE', os.path.join(tempfile.mkdtemp(prefix='rvt-editstore-'), 'es'))
