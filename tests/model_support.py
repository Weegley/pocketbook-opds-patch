"""Synthetic byte fixtures and modeled OS boundaries, never firmware/pbjb files."""
from pathlib import Path
import hashlib
import os
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ.get('OPDS_BUSYBOX') or str(ROOT / '.tools/busybox64.exe') if os.name == 'nt'
            else os.environ.get('OPDS_BUSYBOX') or shutil.which('busybox') or '')
if not HOST.is_file():
    raise RuntimeError('BusyBox required for shell tests; see docs/BUILD.md. Set OPDS_BUSYBOX or run setup.')
CASES = ROOT / '.cache/tests' / str(time.time_ns())
CASES.mkdir(parents=True)
ORIGINAL = b'SYNTHETIC ORIGINAL. NOT POCKETBOOK FIRMWARE.\n'
PATCHED = b'SYNTHETIC PATCHED. NOT POCKETBOOK FIRMWARE.\n'
SU = b'SYNTHETIC SU. NOT EXECUTABLE.\n'
JAILBREAK = b'SYNTHETIC JAILBREAK. NOT EXECUTABLE.\n'

class MemoryFile:
    def __init__(self, data):
        self.data = data
    def read_bytes(self):
        return self.data

def sub_hashes(text):
    for digest, data in [
        ('e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98', ORIGINAL),
        ('c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5', PATCHED),
        ('7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb', SU),
        ('a523b9e77519fa0dd657268c4ad59d3ea1bcb4e07355687e6e372b68ff8c6a10', JAILBREAK),
    ]:
        text = text.replace(digest, hashlib.sha256(data).hexdigest())
    return text
