import tempfile, unittest, time
from pathlib import Path
from unittest.mock import patch
import manager
class RememberTests(unittest.TestCase):
    def test_persist_and_revoke(self):
        with tempfile.TemporaryDirectory() as d, patch.object(manager,'REMEMBER_FILE',Path(d)/'remember.json'):
            token='test-random-secret-token'
            record={'csrf':'abc','expires':time.time()+3600}
            manager.remember_create(token,record)
            self.assertEqual(manager.remember_read()[manager.remember_digest(token)],record)
            self.assertNotIn(token,(Path(d)/'remember.json').read_text())
            manager.remember_revoke(token)
            self.assertEqual(manager.remember_read(),{})
    def test_expired_removed(self):
        with tempfile.TemporaryDirectory() as d, patch.object(manager,'REMEMBER_FILE',Path(d)/'remember.json'):
            manager.remember_create('token',{'csrf':'x','expires':time.time()-1})
            self.assertEqual(manager.remember_read(),{})
if __name__=='__main__': unittest.main()
