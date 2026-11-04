"""Regression: importing the FIT library must not run its command-line entry point."""
import pathlib
import subprocess
import sys

script = pathlib.Path(__file__).resolve().parents[1] / 'scripts/verify-fit.py'
# check-built-images passes directories in argv; the former module body
# attempted to open them as FIT files during exec_module().
program = '''
import importlib.util, sys
spec = importlib.util.spec_from_file_location('fit', sys.argv[1])
sys.argv = ['check-built-images.py', sys.argv[2], sys.argv[2]]
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.verify)
assert callable(module.parse)
'''
subprocess.run([sys.executable, '-c', program, str(script), str(script.parent)], check=True)
print('PASS: FIT module imports with directory arguments without running the CLI')
