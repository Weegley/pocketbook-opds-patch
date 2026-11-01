"""Download pinned tools into this project only, using Python's standard library."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WHEELS = {
    'Windows': ('ziglang-0.13.0-py3-none-win_amd64.whl', 'b64b2aa936ebbfeecfbb2611df331a5474edebe1246b98c2f56d6ae4d58b71fc'),
    'Linux': ('ziglang-0.13.0-py3-none-manylinux_2_12_x86_64.manylinux2010_x86_64.musllinux_1_1_x86_64.whl', '3ce0c9f16547e5d61b32e0d226926e9a2552ef4b91fccf7ab5ea1a623a77824b'),
}
BUSYBOX_SHA = '95343c871869cc0ab57ecec26b2f9af0370eb9c954f7e5ddd017163e4e0d09a0'

def download(url, destination, expected):
    if not destination.resolve().is_relative_to(ROOT):
        raise RuntimeError('Downloads may not escape the project')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file():
        temporary = destination.with_suffix(destination.suffix + '.part')
        request = urllib.request.Request(url, headers={'User-Agent': 'pocketbook-opds-patch-build'})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
            temporary.unlink()
            raise RuntimeError('Downloaded checksum mismatch: ' + url)
        temporary.replace(destination)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Local tool checksum mismatch: ' + str(destination))
    return destination

def setup_zig():
    if platform.machine().lower() not in ['amd64', 'x86_64'] or platform.system() not in WHEELS:
        raise RuntimeError('Automatic tool setup supports Windows/Linux x86-64; provide OPDS_ZIG=Zig 0.13.0 otherwise.')
    filename, expected = WHEELS[platform.system()]
    wheel = ROOT / '.tools/downloads' / filename
    if not wheel.is_file():
        # The version and accepted filename/hash are fixed, never request latest.
        with urllib.request.urlopen('https://pypi.org/pypi/ziglang/0.13.0/json', timeout=30) as response:
            metadata = json.load(response)
        selected = next(item for item in metadata['urls'] if item['filename'] == filename)
        if selected['digests']['sha256'] != expected:
            raise RuntimeError('Pinned wheel metadata mismatch')
        download(selected['url'], wheel, expected)
    elif hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Pinned local wheel mismatch')
    target = ROOT / '.tools/python'
    if not target.resolve().is_relative_to(ROOT):
        raise RuntimeError('Tool install directory escapes the project')
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as archive:
        for item in archive.infolist():
            path = (target / item.filename).resolve()
            if not path.is_relative_to(target.resolve()):
                raise RuntimeError('Unsafe wheel member')
        archive.extractall(target)
    executable = target / 'ziglang' / ('zig.exe' if os.name == 'nt' else 'zig')
    executable.chmod(0o755)
    return executable

def host_shell(setup=False):
    if os.name != 'nt':
        path = ROOT / '.tools/posix-tools'
        path.parent.mkdir(exist_ok=True)
        path.write_text('#!/bin/sh\ncommand=$1\nshift\nexec "$command" "$@"\n', encoding='ascii', newline='\n')
        path.chmod(0o755)
        return path
    path = Path(os.environ.get('OPDS_BUSYBOX', ROOT / '.tools/busybox64.exe')).resolve()
    if not path.is_file() and setup:
        if not path.is_relative_to(ROOT):
            raise RuntimeError('Automatic downloads may only be written inside the project; supply an existing OPDS_BUSYBOX file or use .tools/busybox64.exe')
        download('https://frippery.org/files/busybox/busybox64.exe', path, BUSYBOX_SHA)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != BUSYBOX_SHA:
        raise RuntimeError('Windows shell tests need BusyBox SHA256=' + BUSYBOX_SHA + '. Put it at .tools/busybox64.exe (or set OPDS_BUSYBOX). The official URL is mutable; a changed binary is refused. See docs/BUILD.md.')
    return path
