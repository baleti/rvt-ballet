"""SAVE! of a model on a network/FUSE file system is refused before anything is read or written (simulated mount type); env opt-in lifts it."""
import os, sys, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import save, plat

class T(unittest.TestCase):
    def test_refused(self):
        with mock.patch.object(plat.fsio, 'network_fs_kind', return_value='smbfs'), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('RVTBALLET_ALLOW_NETWORK_OVERWRITE', None)
            with self.assertRaises(save.NetworkFS): save._network_gate('/x/a.rvt')
            self.assertEqual(save.error_status(save.NetworkFS('x')), (409, 'network_fs'))
    def test_optin_and_local(self):
        with mock.patch.object(plat.fsio, 'network_fs_kind', return_value='smbfs'), mock.patch.dict(os.environ, {'RVTBALLET_ALLOW_NETWORK_OVERWRITE': '1'}):
            save._network_gate('/x/a.rvt')
        with mock.patch.object(plat.fsio, 'network_fs_kind', return_value=''): save._network_gate('/x/a.rvt')
if __name__ == '__main__': unittest.main()
