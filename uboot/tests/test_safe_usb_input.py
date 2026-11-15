import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

script = Path(__file__).resolve().parents[1]/'scripts/safe_usb_input.py'
spec=importlib.util.spec_from_file_location('safe_input',script)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Input(unittest.TestCase):
    def test_valid_and_wrong_size(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'input';p.write_bytes(b'abc')
            self.assertEqual(m.read_regular(p,3,3),b'abc')
            for maximum,exact in [(2,None),(4,4)]:
                with self.assertRaises(ValueError):m.read_regular(p,maximum,exact)
    def test_special_files(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'fifo').touch();(root/'fifo').unlink();os.mkfifo(root/'fifo')
            (root/'link').symlink_to('/dev/zero')
            for p in [root/'fifo',root/'link',Path('/dev/zero'),root]:
                with self.subTest(path=str(p)),self.assertRaises((ValueError,OSError)):m.read_regular(p,16)
    def test_sparse_oversize(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'large'
            with p.open('wb') as f:f.truncate(1024**3)
            with self.assertRaises(ValueError):m.read_regular(p,16)
    def test_old_fifo_hang(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fifo';os.mkfifo(p)
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run([sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).read_bytes()',str(p)],timeout=0.5)

if __name__=='__main__':unittest.main()
