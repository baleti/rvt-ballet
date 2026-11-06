"""(+ POSIX ACL via raw system.posix_acl_access xattr, no setfacl needed) In-place SAVE! (set_string edit, 2024 cols2 scene) keeps user xattrs and the 0640 mode of the original file (queue item 12); skips if the filesystem has no user xattrs."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
T = 301595; REFUSED = []
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    hs = [h0]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        os.chmod(src, 0o640)
        try: os.setxattr(src, 'user.c2x_tag', b'keepme')
        except OSError: print('skip (no xattr)'); return
        import struct; ents = [(1, 6, 0xffffffff), (2, 4, 12345), (4, 4, 0xffffffff), (0x10, 4, 0xffffffff), (0x20, 0, 0xffffffff)]      # user_obj rw, named user r, group_obj r, mask r, other -
        acl = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', t, p, i) for t, p, i in ents); ACL = None
        try: os.setxattr(src, 'system.posix_acl_access', acl); ACL = os.getxattr(src, 'system.posix_acl_access')
        except OSError: print('note: ACL xattr not supported here')
        assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'xa', 'match': ''})).status == 200
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200, await r.text()
        assert sha(src) != h0, 'not saved'
        assert os.getxattr(src, 'user.c2x_tag') == b'keepme', 'xattr lost'
        if ACL is None: assert oct(os.stat(src).st_mode & 0o777) == '0o640', oct(os.stat(src).st_mode)
        else: assert os.getxattr(src, 'system.posix_acl_access') == ACL, 'ACL lost or changed'; print('ACL preserved')
    print('save xattr+mode preserved OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
