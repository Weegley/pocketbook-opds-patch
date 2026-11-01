"""Export an explicit source-only allowlist; never traverse local tools/binaries."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = ['.gitattributes', '.gitignore', 'README.md', 'README.ru.md', 'LICENSE',
       'THIRD_PARTY_NOTICES.md', 'SHA256SUMS.txt', 'COMMIT_FILES.txt',
       'build.ps1', 'build.sh', 'dependencies.lock.json', 'requirements-build.txt']
FOLDERS = ['src', 'scripts', 'tests', 'patches', 'docs', 'licenses']
FORBIDDEN = {'.app', '.so', '.exe', '.dll', '.bin', '.img', '.zip', '.whl', '.pyc', '.o', '.tgz'}

def files():
    result = [ROOT / name for name in TOP]
    for directory in FOLDERS:
        result.extend(p for p in (ROOT / directory).rglob('*') if p.is_file())
    for path in result:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or path.suffix.lower() in FORBIDDEN:
            raise RuntimeError('Unsafe source export member: ' + str(path))
        if path.name != 'COMMIT_FILES.txt':
            data = path.read_bytes()
            if b'\x00' in data:
                raise RuntimeError('Binary in source allowlist: ' + str(path))
            data.decode('utf-8')
    return sorted(result)

def main():
    paths = files()
    (ROOT / 'COMMIT_FILES.txt').write_text(''.join(p.relative_to(ROOT).as_posix() + '\n' for p in paths), encoding='utf-8', newline='\n')
    destination = ROOT / 'build/pocketbook-opds-patch-source.zip'
    if not destination.resolve().is_relative_to(ROOT):
        raise RuntimeError('Source archive must stay within the project')
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path in paths:
            name = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo('pocketbook-opds-patch/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o100755 if name == 'build.sh' else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
    print('SOURCE EXPORT:', len(paths), 'text files;', hashlib.sha256(destination.read_bytes()).hexdigest())
    print('Source ZIP:', destination)

if __name__ == '__main__':
    main()
