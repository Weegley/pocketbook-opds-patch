"""Audit default releases: no proprietary library; only exact approved pbjb."""
from pathlib import Path
import hashlib
import io
import tarfile
import zipfile
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_source import files as source_files

ROOT = Path(__file__).resolve().parents[1]

def main():
    files = []
    sums = (ROOT / 'dist/SHA256SUMS.txt').read_text(encoding='ascii').splitlines()
    for line in sums:
        expected, name = line.split('  ', 1)
        if name not in ['Online libraries.app', 'Non-rooted patch.app', 'Rooted patch.app']:
            raise RuntimeError('Unexpected app in public checksum file')
        path = ROOT / 'dist' / name
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Public app SHA mismatch')
        _, payload = data.split(b'__OPDS_DATA__\n', 1)
        with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
            for item in archive:
                if not item.isfile() or item.name.startswith('/') or '..' in Path(item.name).parts:
                    raise RuntimeError('Unsafe public archive')
                if item.name == 'Jailbreak.app' or 'libopds_app_lib.so' in item.name:
                    raise RuntimeError('Forbidden firmware/wrapper in app')
                if item.name.endswith('.so') and item.name != 'libpb_opds_host.so':
                    raise RuntimeError('Unknown shared library in public app')
                content = archive.extractfile(item).read()
                if item.name.startswith('pbjb/'):
                    hashes = {'pbjb/jailbreak': 'a523b9e77519fa0dd657268c4ad59d3ea1bcb4e07355687e6e372b68ff8c6a10',
                              'pbjb/su': '7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb'}
                    if name != 'Non-rooted patch.app' or item.name not in hashes or hashlib.sha256(content).hexdigest() != hashes[item.name]:
                        raise RuntimeError('Unknown/unapproved pbjb component')
                if len(content) in [598364, 610748]:
                    raise RuntimeError('Firmware-sized public member')
        files.append((name, data))
    if len(files) != 3 or len({n for n, _ in files}) != 3:
        raise RuntimeError('Exactly three default public apps required')
    for source in source_files():
        if source.name != 'SHA256SUMS.txt':
            files.append((source.relative_to(ROOT).as_posix(), source.read_bytes()))
    files.append(('SHA256SUMS.txt', (ROOT / 'dist/SHA256SUMS.txt').read_bytes()))
    path = ROOT / 'build/pocketbook-opds-patch-v9-public.zip'
    if not path.resolve().is_relative_to(ROOT):
        raise RuntimeError('Release archive must remain inside project')
    path.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print('PUBLIC RELEASE:', path, hashlib.sha256(path.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
