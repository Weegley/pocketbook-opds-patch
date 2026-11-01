"""Obtain pinned pbjb files locally for Non-rooted packaging; never commit inputs."""
from pathlib import Path
import argparse
import hashlib
import shutil
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '8f1fb889d575237f2b292e88df6aabf552142d87'
FILES = {'jailbreak': 'a523b9e77519fa0dd657268c4ad59d3ea1bcb4e07355687e6e372b68ff8c6a10',
         'su': '7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb'}

def obtain_components(source=None):
    target = ROOT / 'external/pbjb'
    if not target.resolve().is_relative_to(ROOT):
        raise RuntimeError('External dependency directory must remain inside the project')
    target.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        destination = target / name
        if destination.is_symlink():
            raise RuntimeError('Unsafe external component symlink')
        if destination.exists():
            if not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
                raise RuntimeError('Refusing to overwrite a different local component: ' + str(destination))
            print(name + ': existing local SHA256 verified', flush=True)
            continue
        if source:
            data = (source / name).read_bytes()
        else:
            url = f'https://raw.githubusercontent.com/ezdiy/pbjb/{COMMIT}/{name}'
            print('Downloading pinned pbjb ' + name + ' ...', flush=True)
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Refused ' + name + ': expected SHA256=' + expected)
        temporary = target / (name + '.part')
        temporary.write_bytes(data)
        temporary.replace(destination)
        print(name + ': SHA256 verified; stored only in ignored external/pbjb/')
    print('Default Non-rooted builds embed these exact files. Git/source exports exclude external/.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--download', action='store_true', help='Fetch the pinned upstream binaries for your local use; no license is implied')
    choice.add_argument('--from', dest='source', type=Path, help='Directory containing your original upstream jailbreak and su')
    args = parser.parse_args()
    try:
        obtain_components(args.source)
        return 0
    except (OSError, RuntimeError) as error:
        print('ERROR: pbjb acquisition failed: ' + str(error), file=sys.stderr)
        print('Check network/upstream SHA, or use --from DIR with the pinned upstream files. See docs/PBJB.md.', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
