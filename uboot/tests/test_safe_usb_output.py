import importlib.util
from pathlib import Path
import os
import tempfile
import unittest

module = Path(__file__).resolve().parents[1] / 'scripts/safe_usb_output.py'
spec = importlib.util.spec_from_file_location('safe_output', module)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SafeOutput(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            m.stage_files(t, {'mtd0.bin': b'example', 'SHA256SUMS': b'hash'})
            m.stage_files(t, {'mtd0.bin': b'example', 'SHA256SUMS': b'hash'})
            self.assertEqual((Path(t)/'XSW250NS-STOCK/mtd0.bin').read_bytes(), b'example')
    def test_hostile_outputs(self):
        for attack in ['directory-link', 'manifest-link', 'dangling-link', 'fifo', 'hardlink', 'different-file']:
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as t:
                root=Path(t); victim=root/'victim';victim.write_bytes(b'KEEP')
                out=root/'XSW250NS-STOCK'
                if attack=='directory-link':out.symlink_to(root, target_is_directory=True)
                else:
                    out.mkdir();p=out/'SHA256SUMS'
                    if attack=='manifest-link':p.symlink_to(victim)
                    elif attack=='dangling-link':p.symlink_to(root/'missing')
                    elif attack=='fifo':os.mkfifo(p)
                    elif attack=='hardlink':os.link(victim,p)
                    else:p.write_bytes(b'OLD')
                with self.assertRaises((OSError,ValueError)):m.stage_files(root, {'SHA256SUMS':b'NEW'})
                self.assertEqual(victim.read_bytes(),b'KEEP')
                self.assertFalse((root/'missing').exists())
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):m.stage_files(t, {'../outside':b'x'})

if __name__=='__main__':unittest.main()
