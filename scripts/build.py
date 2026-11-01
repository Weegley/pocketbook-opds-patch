"""Native Windows/Linux build. All installed files/caches stay below ROOT."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import traceback
from datetime import datetime
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.dont_write_bytecode = True
LOG_PATH = None
PBJB = {'jailbreak': 'a523b9e77519fa0dd657268c4ad59d3ea1bcb4e07355687e6e372b68ff8c6a10',
        'su': '7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb'}
REQUIRED_SOURCES = ['scripts/setup_tools.py', 'scripts/get_pbjb.py', 'src/patcher/patcher.c',
                    'src/launcher/opds_release_host.c', 'src/launcher/opds_open_callback.cpp',
                    'src/launcher/opds_open_callback.h', 'src/launcher/release.exports',
                    'patches/U632-6.11.2001/navigation-subtitle.s']

class BuildError(RuntimeError):
    """An actionable build/setup failure, reported without a console traceback."""

def write_log(message):
    global LOG_PATH
    if LOG_PATH is not None:
        try:
            with LOG_PATH.open('a', encoding='utf-8') as stream:
                stream.write(message + '\n')
        except OSError as error:
            LOG_PATH = None
            print('[WARNING] Diagnostic log is unavailable: ' + str(error), flush=True)

def info(message):
    print(message, flush=True)
    write_log(message)

def initialize_environment():
    global LOG_PATH
    LOG_PATH = None
    if sys.version_info < (3, 11):
        raise BuildError('Python 3.11 or newer is required; use Python 3.14.2 for the recorded build.')
    os.chdir(ROOT)
    for key, subdir in {
        'TMP': '.cache/tmp', 'TEMP': '.cache/tmp', 'TMPDIR': '.cache/tmp',
        'ZIG_GLOBAL_CACHE_DIR': '.cache/zig-global', 'ZIG_LOCAL_CACHE_DIR': '.cache/zig-local',
        'XDG_CACHE_HOME': '.cache/xdg', 'PIP_CACHE_DIR': '.cache/pip',
    }.items():
        directory = ROOT / subdir
        if not directory.resolve().is_relative_to(ROOT):
            raise BuildError('Build cache may not point outside the project: ' + str(directory))
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(directory)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PIP_CONFIG_FILE'] = os.devnull
    os.environ['SOURCE_DATE_EPOCH'] = '0'
    directory = ROOT / 'build'
    if not directory.resolve().is_relative_to(ROOT):
        raise BuildError('Build/log directory may not point outside the project.')
    directory.mkdir(exist_ok=True)
    LOG_PATH = directory / 'build.log'
    if not LOG_PATH.resolve().is_relative_to(ROOT):
        LOG_PATH = None
        raise BuildError('Build log may not point outside the project.')
    write_log('\n=== Build invocation: ' + datetime.now().isoformat(timespec='seconds') + ' ===')

def setup_command(args):
    flags = []
    if args.test:
        flags.append('-Test' if os.name == 'nt' else '--test')
    if args.external_pbjb:
        flags.append('-ExternalPbjb' if os.name == 'nt' else '--external-pbjb')
    if args.local_pbjb:
        flags.append('-LocalPbjb' if os.name == 'nt' else '--local-pbjb')
    return (('powershell -ExecutionPolicy Bypass -File .\\build.ps1 ' if os.name == 'nt' else 'sh build.sh ') + ' '.join(flags)).rstrip()

def preflight(args):
    """Inspect all dependencies before downloading or compiling anything."""
    from setup_tools import BUSYBOX_SHA, host_shell
    info('[CHECK] Project: ' + str(ROOT))
    info('[OK] Python ' + sys.version.split()[0] + ': ' + sys.executable)
    info('[INFO] Tools, downloads, logs and caches stay inside this project.')
    errors = []
    missing = []
    absent = [name for name in REQUIRED_SOURCES if not (ROOT / name).is_file()]
    if absent:
        errors.append('Incomplete source tree: ' + ', '.join(absent) + '. Extract the complete source ZIP.')
    if args.test and any(character.isspace() for character in str(ROOT)):
        errors.append('Shell OS-model tests require a project path without whitespace; use a folder such as D:\\Work\\pocketbook-opds-patch.')
    found = find_compiler()
    zig = None
    if found:
        try:
            zig = compiler()
            info('[OK] Zig 0.13.0: ' + zig)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            errors.append('Zig cannot be used: ' + str(error) + '. Check OPDS_ZIG/PATH; select Zig 0.13.0 or clear OPDS_ZIG and use -Setup/--setup.')
    else:
        info('[MISSING] Zig 0.13.0 (local compiler or OPDS_ZIG/PATH).')
        missing.append('zig')
    if not args.external_pbjb or args.local_pbjb:
        for name, expected in PBJB.items():
            path = ROOT / 'external/pbjb' / name
            if not path.exists() and not path.is_symlink():
                info('[MISSING] pbjb: external/pbjb/' + name)
                missing.append('pbjb')
            elif path.is_symlink() or not path.is_file() or sha(path.read_bytes()) != expected:
                errors.append('pbjb ' + name + ' has an unexpected type/SHA-256: ' + str(path) + '. Expected ' + expected + '; verify your upstream copy. It will not be overwritten automatically.')
            else:
                info('[OK] pbjb ' + name + ': SHA-256 verified.')
    else:
        info('[INFO] External-pbjb mode: no pbjb files needed to build.')
    shell = None
    if args.test:
        if os.name == 'nt':
            path = Path(os.environ.get('OPDS_BUSYBOX', ROOT / '.tools/busybox64.exe')).resolve()
            if not path.exists():
                if not path.is_relative_to(ROOT):
                    errors.append('OPDS_BUSYBOX points to a missing external file. Supply an existing file or clear OPDS_BUSYBOX to use local .tools/busybox64.exe.')
                else:
                    info('[MISSING] Windows test shell: .tools/busybox64.exe')
                    missing.append('shell')
            elif not path.is_file() or sha(path.read_bytes()) != BUSYBOX_SHA:
                errors.append('BusyBox SHA-256 mismatch: ' + str(path) + '. Obtain the pinned version from docs/BUILD.md; it will not be overwritten.')
            else:
                shell = path
                info('[OK] Windows test shell: SHA-256 verified.')
        else:
            for name in ['sh', 'awk', 'sed', 'grep', 'tar', 'sha256sum', 'flock']:
                if shutil.which(name) is None:
                    errors.append('Missing POSIX test prerequisite: ' + name)
    else:
        info('[INFO] Offline installer tests not requested; use -Test/--test to run them.')
    for message in errors:
        info('[ERROR] ' + message)
    if missing:
        info('[INFO] Missing inputs are downloaded automatically during a normal build (network access required).')
        info('  ' + setup_command(args))
        info('[INFO] Setup verifies pinned versions/SHA-256; no global installs. See docs/BUILD.md / docs/BUILD.ru.md.')
    if errors or (missing and (not args.setup or args.check)):
        raise BuildError('Preflight failed. No compilation was started; existing .app files were not changed.')
    if missing:
        if 'zig' in missing:
            from setup_tools import setup_zig
            info('[SETUP] Obtaining pinned Zig 0.13.0 into .tools/python (first setup may take several minutes).')
            try:
                setup_zig()
                zig = compiler()
            except Exception as error:
                raise BuildError('Zig setup failed: ' + str(error) + '. Check network/proxy/certificates or provide the pinned wheel as documented in docs/BUILD.md.') from error
        if 'pbjb' in missing:
            from get_pbjb import obtain_components
            info('[SETUP] Obtaining pinned pbjb files into external/pbjb; checking SHA-256.')
            try:
                obtain_components()
            except Exception as error:
                raise BuildError('pbjb setup failed: ' + str(error) + '. Check network access, or import an upstream copy with scripts/get_pbjb.py --from DIR.') from error
        if 'shell' in missing:
            info('[SETUP] Obtaining the pinned Windows test shell into .tools/.')
            try:
                shell = host_shell(True)
            except Exception as error:
                raise BuildError('Test-shell setup failed: ' + str(error) + '. See the pinned version/hash in docs/BUILD.md.') from error
    if args.test:
        shell = shell or host_shell()
        os.environ['OPDS_BUSYBOX'] = str(shell)
    info('[OK] Preflight passed.' + (' Check-only: no downloads or compilation requested.' if args.check else ' Ready to compile.'))
    return zig

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(args, label='Running build tool'):
    info('[BUILD] ' + label)
    command = [str(x) for x in args]
    write_log('COMMAND: ' + subprocess.list2cmdline(command))
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    for output in [result.stdout, result.stderr]:
        if output:
            write_log(output.rstrip())
    if result.returncode:
        raise BuildError(label + ' failed (exit code ' + str(result.returncode) + '). Compiler/test output is saved in build/build.log.')
    for output in [result.stdout, result.stderr]:
        if output:
            print(output, end='' if output.endswith('\n') else '\n', flush=True)

def find_compiler():
    local = ROOT / '.tools/python/ziglang' / ('zig.exe' if os.name == 'nt' else 'zig')
    return os.environ.get('OPDS_ZIG') or (str(local) if local.is_file() else None)

def compiler(setup=False):
    path = find_compiler()
    if not path and setup:
        from setup_tools import setup_zig
        path = str(setup_zig())
    if not path:
        raise RuntimeError('Zig 0.13.0 required: run build.ps1 -Setup / sh build.sh --setup, or set OPDS_ZIG to an existing compiler. Installs only to .tools/python.')
    path = str(Path(path).resolve())
    version = subprocess.check_output([path, 'version'], text=True, stderr=subprocess.STDOUT, timeout=10).strip()
    if version != '0.13.0':
        raise RuntimeError('Zig version must be exactly 0.13.0; got ' + version)
    return path

def compile_all(zig):
    out = ROOT / 'build'
    if not out.resolve().is_relative_to(ROOT):
        raise RuntimeError('Build directory escapes project')
    out.mkdir(exist_ok=True)
    common = ['-O2', '-s', '-fno-ident', '-ffile-prefix-map=' + str(ROOT) + '=.', '-Wl,--build-id=none']
    target = ['-target', 'arm-linux-gnueabi.2.19', '-mcpu=cortex_a8']
    run([zig, 'cc', *target, '-c', 'patches/U632-6.11.2001/navigation-subtitle.s', '-o', 'build/helpers.o'], 'Assembling ARM patch helpers')
    run([zig, 'cc', *common, '-target', 'arm-linux-musleabi', '-mcpu=cortex_a8', '-static',
         'src/patcher/patcher.c', '-o', 'build/opds-patcher'], 'Compiling the on-device ARM patcher')
    host = 'build/patcher-host' + ('.exe' if os.name == 'nt' else '')
    run([zig, 'cc', '-O2', '-std=c11', 'src/patcher/patcher.c', '-o', host], 'Compiling the native patcher test tool')
    run([ROOT / host, '--self-test'], 'Checking the patcher SHA-256 implementation')
    stubs = 'src/launcher/link-stubs/'
    for name, filename in [('stdcxx', 'libstdc++.so.6'), ('gcc', 'libgcc_s.so.1')]:
        run([zig, 'cc', *common, *target, '-fPIC', '-shared', '-nostdlib', stubs + name + '.c',
             '-Wl,-soname,' + filename, '-Wl,--version-script=' + stubs + name + '.map', '-o', out / filename], 'Building link-only ABI declarations: ' + filename)
    run([zig, 'cc', *common, *target, '-fPIC', '-shared', '-fvisibility=hidden', '-fno-stack-protector',
         '-funwind-tables', '-fno-optimize-sibling-calls', '-fno-exceptions', '-nostdinc++', '-nostdlib++',
         '-DPB_OPDS_RELEASE', '-Wl,-soname,libpb_opds_host.so', '-Wl,-z,relro,-z,now', '-Wl,--gc-sections',
         '-Wl,--version-script=src/launcher/release.exports', 'src/launcher/opds_release_host.c',
         'src/launcher/opds_open_callback.cpp', '-Wl,--no-as-needed', 'build/libstdc++.so.6',
         'build/libgcc_s.so.1', '-Wl,--as-needed', '-ldl', '-o', 'build/libpb_opds_host.so'], 'Compiling the OPDS launcher')
    if sha((out / 'libpb_opds_host.so').read_bytes()) != '4e973c3616e728a4c7954b6a0e888bd64df55841485743adfb74d2eed8cfdc43':
        raise RuntimeError('Source-built host differs from universal-v8; refusing to present it as the tested host')
    run([zig, 'c++', '-O1', '-DPB_OPDS_RELEASE', 'src/launcher/callback_host_test.cpp', '-o',
         'build/callback-test' + ('.exe' if os.name == 'nt' else '')], 'Compiling the native callback model')
    run([out / ('callback-test.exe' if os.name == 'nt' else 'callback-test')], 'Running the native callback model')

def stored_gzip(data):
    # Stored DEFLATE blocks: identical output independent of zlib/Python versions.
    blocks = bytearray()
    for pos in range(0, len(data), 65535):
        block = data[pos:pos + 65535]
        blocks += bytes([int(pos + len(block) == len(data))])
        blocks += struct.pack('<HH', len(block), len(block) ^ 65535) + block
    return b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff' + blocks + struct.pack('<II', zlib.crc32(data), len(data))

def package(policy, local_pbjb=False):
    source = ROOT / 'src/installer'
    common = ['i18n.sh', 'prepare-library.sh']
    if policy != 'none':
        common += ['opds-system.sh', 'physical-common.sh', 'physical-recover.sh']
    if policy == 'remove':
        common += ['pbjb-components.sh']
    members = {'scripts/' + name: (source / 'common' / name).read_bytes() for name in common}
    members.update({'scripts/' + p.name: p.read_bytes() for p in sorted((source / policy).glob('*.sh'))})
    members['tools/opds-patcher'] = (ROOT / 'build/opds-patcher').read_bytes()
    for license_path in sorted((ROOT / 'licenses').iterdir()):
        members['licenses/' + license_path.name] = license_path.read_bytes()
    if policy == 'none':
        members['libpb_opds_host.so'] = (ROOT / 'build/libpb_opds_host.so').read_bytes()
        members['scripts/standalone.sh'] = members['scripts/standalone.sh'].replace(b'@HOST_SHA@', sha(members['libpb_opds_host.so']).encode())
    if policy == 'remove' and local_pbjb:
        for name, expected in PBJB.items():
            path = ROOT / 'external/pbjb' / name
            if not path.is_file() or sha(path.read_bytes()) != expected:
                raise RuntimeError('Obtain pinned pbjb ' + name + ' at external/pbjb/' + name + '; see docs/PBJB.md. SHA-256 must be ' + expected)
            members['pbjb/' + name] = path.read_bytes()
    manifest = ''.join(sha(data) + '  ' + name + '\n' for name, data in sorted(members.items())).encode()
    members['SHA256SUMS'] = manifest
    tar = io.BytesIO()
    with tarfile.open(fileobj=tar, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(members.items()):
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o755 if name.endswith('.sh') or name.startswith(('tools/', 'pbjb/')) else 0o644
            archive.addfile(item, io.BytesIO(data))
    payload = stored_gzip(tar.getvalue())
    header = (source / policy / 'sfx-header.sh.in').read_text(encoding='utf-8')
    header = header.replace('@I18N@', (source / 'common/i18n.sh').read_text(encoding='utf-8'))
    for before, after in [('@ARCHIVE_SHA@', sha(payload)), ('@MANIFEST_SHA@', sha(manifest))]:
        if header.count(before) != 1:
            raise RuntimeError('Missing header anchor ' + before)
        header = header.replace(before, after)
    return header.encode() + payload

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true', help='Compatibility alias: missing inputs are now prepared automatically')
    parser.add_argument('--offline', action='store_true', help='Never download; require cached inputs or explicit tool overrides')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--local-pbjb', action='store_true')
    parser.add_argument('--external-pbjb', action='store_true', help='Optional non-embedded pbjb variant; default embeds the exact upstream files')
    parser.add_argument('--check', action='store_true', help='Inspect prerequisites only; never download or compile')
    parser.add_argument('--debug', action='store_true', help='Also print a diagnostic traceback on failure')
    args = parser.parse_args(argv)
    args.setup = not (args.check or args.offline)
    initialize_environment()
    zig = preflight(args)
    if args.check:
        return 0
    if args.test:
        run([sys.executable, '-B', 'tests/test_build.py'], 'Running build-preflight regression tests (no network or compiler execution)')
        run([sys.executable, '-B', 'tests/test_bootstrap.py'], 'Running portable-Python bootstrap regression tests (synthetic archives only)')
    embedded = not args.external_pbjb
    compile_all(zig)
    files = [('none', 'Online libraries.app'), ('remove', 'Non-rooted patch.app'), ('keep', 'Rooted patch.app')]
    if args.local_pbjb:
        package('remove', True)  # Validate private inputs before writing outputs.
    outputs = {}
    for local in ([False, True] if args.local_pbjb else [False]):
        dest = ROOT / ('dist-local' if local else 'dist')
        if not dest.resolve().is_relative_to(ROOT):
            raise RuntimeError('Distribution directory escapes project')
        dest.mkdir(exist_ok=True)
        sums = []
        for policy, name in files:
            info('[PACKAGE] ' + name)
            data = package(policy, local or embedded)
            (dest / name).write_bytes(data)
            sums.append(sha(data) + '  ' + name + '\n')
        (dest / 'SHA256SUMS.txt').write_text(''.join(sums), encoding='ascii', newline='\n')
        outputs[dest.name] = sums
        info('[OK] Apps and SHA256SUMS.txt saved in ' + str(dest))
    report = {'platform': sys.platform, 'python': sys.version.split()[0], 'zig': '0.13.0',
              'pbjb_embedded_in_nonrooted': embedded, 'additional_local_copy': args.local_pbjb, 'artifacts': outputs}
    (ROOT / 'build/build-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.test:
        os.environ['OPDS_EMBED_PBJB'] = '1' if embedded else '0'
        run([sys.executable, '-B', 'tests/run_tests.py'], 'Running offline installer/package tests (this can take several minutes)')
    info('[SUCCESS] Build completed. Checksums: dist/SHA256SUMS.txt')
    return 0

def cli(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    try:
        return main(arguments)
    except KeyboardInterrupt:
        info('[CANCELLED] Build interrupted by the user.')
        return 130
    except Exception as error:
        write_log(traceback.format_exc())
        info('[ERROR] ' + str(error))
        if LOG_PATH is not None:
            info('[INFO] Diagnostic log: ' + str(LOG_PATH))
        info('[INFO] For a console traceback, use -DebugBuild / --debug.')
        if '--debug' in arguments:
            traceback.print_exc()
        return 2 if isinstance(error, BuildError) else 1

if __name__ == '__main__':
    sys.exit(cli())
