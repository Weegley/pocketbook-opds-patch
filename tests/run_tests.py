"""Offline tests. No ARM execution, root, real mount or device access."""
from pathlib import Path
import hashlib
import io
import json
import os
import re
import runpy
import struct
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if any(character.isspace() for character in str(ROOT)):
    raise RuntimeError('Shell OS-model tests require a project path without whitespace; app compilation/packaging supports spaces. See docs/BUILD.md.')
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT / 'scripts'))
builder = runpy.run_path(str(ROOT / 'scripts/build.py'))
builder['initialize_environment']()
from setup_tools import host_shell
os.environ['OPDS_BUSYBOX'] = str(host_shell())
from model_support import HOST, CASES, ORIGINAL, PATCHED, SU, JAILBREAK, sub_hashes
results = []

def check(condition, name):
    if not condition:
        raise AssertionError(name)
    results.append(name)
    if len(results) % 50 == 0:
        print('Offline checks completed:', len(results), flush=True)

def shell(path, *args, expected=0):
    p = subprocess.run([str(HOST), 'sh', str(path), *map(str, args)], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=30)
    if p.returncode != expected:
        raise AssertionError(f'{path}: expected {expected}, got {p.returncode}\n{p.stdout}{p.stderr}')
    return p

def unpack(data):
    header, compressed = data.split(b'__OPDS_DATA__\n', 1)
    with tarfile.open(fileobj=io.BytesIO(compressed), mode='r:gz') as archive:
        infos = archive.getmembers()
        assert len({i.name for i in infos}) == len(infos)
        assert all(i.isfile() and not i.name.startswith('/') and '..' not in Path(i.name).parts and not i.mode & 0o6000 for i in infos)
        return header, {i.name: archive.extractfile(i).read() for i in infos}

for path in sorted((ROOT / 'src/installer').rglob('*.sh')):
    p = subprocess.run([str(HOST), 'sh', '-n', str(path)], capture_output=True)
    check(p.returncode == 0, 'syntax:' + path.relative_to(ROOT).as_posix())

apps = {}
embedded = os.environ.get('OPDS_EMBED_PBJB', '1') == '1'
for policy, name in [('none', 'Online libraries.app'), ('remove', 'Non-rooted patch.app'), ('keep', 'Rooted patch.app')]:
    data = (ROOT / 'dist' / name).read_bytes()
    check(data == builder['package'](policy, embedded) == builder['package'](policy, embedded), 'deterministic-package:' + policy)
    header, members = unpack(data)
    p = subprocess.run([str(HOST), 'sh', '-n'], input=header, capture_output=True)
    check(p.returncode == 0 and b'@' not in header, 'sfx-template-complete:' + policy)
    manifest = dict((line.split('  ', 1)[1], line.split('  ', 1)[0]) for line in members['SHA256SUMS'].decode().splitlines())
    check(set(manifest) == set(members) - {'SHA256SUMS'} and all(hashlib.sha256(members[n]).hexdigest() == h for n, h in manifest.items()), 'packed-manifest:' + policy)
    check(all(n != 'Jailbreak.app' and 'libopds_app_lib.so' not in n for n in members), 'public-payload-has-no-firmware-library:' + policy)
    bundled = {n: b for n, b in members.items() if n.startswith('pbjb/')}
    wanted = {'pbjb/' + n: h for n, h in builder['PBJB'].items()} if policy == 'remove' and embedded else {}
    check(set(bundled) == set(wanted) and all(hashlib.sha256(b).hexdigest() == wanted[n] for n, b in bundled.items()), 'exact-upstream-pbjb-only-where-requested:' + policy)
    check(all(len(b) not in [598364, 610748] for b in members.values()), 'no-full-firmware-sized-members:' + policy)
    check(members['tools/opds-patcher'][:7] == b'\x7fELF\x01\x01\x01' and struct.unpack_from('<H', members['tools/opds-patcher'], 18)[0] == 40, 'ARM-patcher-not-executed:' + policy)
    check((policy == 'none') == ('libpb_opds_host.so' in members), 'launcher-only-in-online-libraries:' + policy)
    apps[policy] = (header, members)

patcher = ROOT / ('build/patcher-host.exe' if os.name == 'nt' else 'build/patcher-host')
obj = (ROOT / 'build/helpers.o').read_bytes()
section_offset = struct.unpack_from('<I', obj, 32)[0]
section_count, strings_index = struct.unpack_from('<HH', obj, 48)
strings_offset, strings_size = struct.unpack_from('<II', obj, section_offset + strings_index * 40 + 16)
strings = obj[strings_offset:strings_offset + strings_size]
assembled = None
for index in range(section_count):
    name_offset = struct.unpack_from('<I', obj, section_offset + index * 40)[0]
    if strings[name_offset:].split(b'\0', 1)[0] == b'.text':
        offset, size = struct.unpack_from('<II', obj, section_offset + index * 40 + 16)
        assembled = obj[offset:offset + size]
words = (ROOT / 'src/patcher/patcher.c').read_text(encoding='utf-8').split('static const uint32_t code[]={', 1)[1].split('};', 1)[0]
expected_words = [int(word, 16) for word in re.findall(r'0x[0-9a-f]+', words)]
check(assembled == struct.pack('<' + 'I' * len(expected_words), *expected_words), 'ARM-assembly-matches-C-patcher-instruction-words')
check(subprocess.run([str(patcher), '--self-test'], capture_output=True).returncode == 0, 'native-patcher-SHA-self-test')
for case, model, version, content in [('wrong-model', 'Pocket634', 'U632.6.11.2001', b'x'),
        ('wrong-version', 'Pocket632', 'U632.6.5.1383', b'x'), ('wrong-size', 'Pocket632', 'U632.6.11.2001', b'x'),
        ('wrong-SHA', 'Pocket632', 'U632.6.11.2001', bytes(598364)), ('already-patched-size', 'Pocket632', 'U632.6.11.2001', bytes(610748))]:
    f = CASES / case
    f.mkdir()
    (f / 'input').write_bytes(content)
    p = subprocess.run([str(patcher), model, version, str(f / 'input'), str(f / 'output')], capture_output=True)
    check(p.returncode != 0 and not (f / 'output').exists() and (f / 'input').read_bytes() == content, 'patcher-refusal-preserves-input:' + case)

private = {'performed': False, 'reason': 'Set OPDS_ORIGINAL and OPDS_REFERENCE to private, external files. No firmware is required for public tests.'}
if os.environ.get('OPDS_ORIGINAL') and os.environ.get('OPDS_REFERENCE'):
    original = Path(os.environ['OPDS_ORIGINAL']).resolve()
    reference = Path(os.environ['OPDS_REFERENCE']).resolve()
    check(not original.is_relative_to(ROOT) and not reference.is_relative_to(ROOT), 'private-inputs-outside-repository')
    p = subprocess.run([str(patcher), 'Pocket632', 'U632.6.11.2001', str(original), '--compare', str(reference)], capture_output=True, text=True)
    check(p.returncode == 0 and 'EXACT_BYTE_MATCH' in p.stdout, 'private-real-original-exact-universal-v8-comparison')
    p = subprocess.run([str(patcher), 'Pocket632', 'U632.6.11.2001', str(reference), str(CASES / 'should-not-exist')], capture_output=True)
    check(p.returncode != 0 and not (CASES / 'should-not-exist').exists(), 'private-repeat-patch-refused')
    occupied = CASES / 'occupied-output'
    occupied.write_bytes(b'unchanged sentinel')
    p = subprocess.run([str(patcher), 'Pocket632', 'U632.6.11.2001', str(original), str(occupied)], capture_output=True)
    check(p.returncode != 0 and occupied.read_bytes() == b'unchanged sentinel', 'private-valid-patch-never-overwrites-existing-output')
    private = {'performed': True, 'method': 'In-memory C patcher comparison; no firmware file written', 'result_sha256': 'c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5'}

# Original installer control flow, with only Linux OS boundaries and input hashes
# modeled. Fixture bytes are visibly synthetic, not firmware or root executables.
core = runpy.run_path(str(ROOT / 'tests/core_regressions.py'))
results.extend('core:' + str(item) for item in core['results'])
import model_transaction as transaction

def invoke(f, script, policy, mode, action, expected=0, consent=True):
    args = [mode, action]
    if policy == 'remove' and mode == 'stage' and consent:
        args.append('remove-existing-root-confirmed')
    return transaction.call(f, script, *args, expected=expected)

def completed(f, policy, action):
    check(transaction.state(f) == 'complete', 'complete:' + f.name)
    check((f / 'mnt/secure/su').exists() == (policy == 'keep'), 'root-policy:' + f.name)
    check(not list((f / 'mnt/secure/runonce').glob('*.sh')), 'no-hook-left:' + f.name)
    check((f / 'ebrmain/cramfs/lib/libopds_app_lib.so').read_bytes() == ORIGINAL, 'SquashFS-preserved:' + f.name)
    check('ext2 ro,relatime,errors=remount-ro' in (f / 'proc/mounts').read_text(), 'read-only-restored:' + f.name)

for policy in ['keep', 'remove']:
    transaction.POLICY = policy
    transaction.HERE = ROOT / 'src/installer' / policy
    f, script = transaction.make(policy + '-roundtrip')
    before = transaction.target(f).read_bytes()
    invoke(f, script, policy, 'stage', 'install')
    invoke(f, script, policy, 'stage', 'install')
    check(transaction.target(f).read_bytes() == before and not (f / 'mount-calls').exists(), 'staging-never-writes-p8:' + policy)
    transaction.boot(f)
    completed(f, policy, 'install')
    check(transaction.target(f).read_bytes() == PATCHED, 'installed-payload:' + policy)
    (f / 'mnt/secure/su').write_bytes(SU)
    invoke(f, script, policy, 'stage', 'uninstall')
    check(transaction.target(f).read_bytes() == PATCHED, 'deferred-uninstall:' + policy)
    transaction.boot(f)
    completed(f, policy, 'uninstall')
    check(transaction.target(f).read_bytes() == before, 'exact-link-restoration:' + policy)
    if policy == 'keep':
        check(not (f / 'chattr-calls').exists(), 'Rooted-never-modifies-root-attributes')
    for fault in ['wrong-version', 'wrong-model', 'wrong-helper', 'unknown-library', 'foreign-hook', 'write-failure', 'interrupted-write', 'cleanup-failure', 'damaged-runtime', 'late-hook', 'remount-failure']:
        f, script = transaction.make(policy + '-' + fault)
        before = transaction.target(f).read_bytes()
        if fault in ['wrong-version', 'wrong-model', 'wrong-helper', 'unknown-library', 'foreign-hook']:
            if fault == 'wrong-version': (f / 'ebrmain/.version').write_text('ver=6.5.1383\n')
            if fault == 'wrong-model': (f / 'ebrmain/config/device.cfg').write_text('model=Pocket634\nvariant=U632\n')
            if fault == 'wrong-helper': (f / 'mnt/secure/su').write_bytes(b'unknown')
            if fault == 'unknown-library': transaction.target(f).write_bytes(b'unknown')
            if fault == 'foreign-hook': (f / 'mnt/secure/runonce/foreign.sh').write_text('do-not-delete')
            snapshot = transaction.target(f).read_bytes()
            invoke(f, script, policy, 'stage', 'install', expected=1)
            check(transaction.target(f).read_bytes() == snapshot and not (f / 'mount-calls').exists(), 'unsafe-stage-refused:' + policy + ':' + fault)
            continue
        invoke(f, script, policy, 'stage', 'install')
        if fault == 'write-failure': (f / 'fail-copy').touch()
        if fault == 'interrupted-write':
            transaction.target(f).write_bytes(b'torn synthetic write')
            (f / 'mnt/secure/opds-authors-6.11/oneapp-phase').write_text('writing\n')
            (f / 'mnt/secure/opds-authors-6.11/lock').mkdir()
        if fault == 'cleanup-failure': (f / 'fail-chattr').touch()
        if fault == 'damaged-runtime': (f / 'mnt/secure/opds-authors-6.11/oneapp-runtime/payload/libopds_app_lib.so').write_bytes(b'damaged')
        if fault == 'remount-failure': (f / 'fail-ro').touch()
        if fault == 'late-hook':
            transaction.call(f, f / 'mnt/secure/opds-authors-6.11/oneapp-runtime/scripts/oneapp-root.sh', 'boot', expected=1)
        else:
            transaction.boot(f, expected=1 if fault in ['damaged-runtime', 'remount-failure'] or (fault == 'cleanup-failure' and policy == 'remove') else 0)
        if fault in ['write-failure', 'interrupted-write']:
            completed(f, policy, 'install')
            check(transaction.target(f).read_bytes() == before, 'failed-write-restores-link:' + policy + ':' + fault)
        if fault in ['late-hook', 'damaged-runtime', 'remount-failure'] or (fault == 'cleanup-failure' and policy == 'remove'):
            check((f / 'mnt/secure/su').exists() and transaction.state(f) != 'complete', 'failure-keeps-recovery-root:' + policy + ':' + fault)
        if fault == 'cleanup-failure' and policy == 'remove':
            (f / 'fail-chattr').unlink()
            invoke(f, script, policy, 'stage', 'install')
            transaction.boot(f)
            completed(f, policy, 'install')
    if policy == 'remove':
        f, script = transaction.make('consent-required')
        invoke(f, script, policy, 'stage', 'install', expected=1, consent=False)
        check((f / 'mnt/secure/su').read_bytes() == SU and not (f / 'mount-calls').exists(), 'backend-refuses-root-removal-without-consent')
        f, script = transaction.make('temporary-root-bootstrap')
        (f / 'mnt/secure/su').unlink()
        invoke(f, script, policy, 'bootstrap', 'install')
        transaction.boot(f)
        completed(f, policy, 'install')

# Preparation executes as a normal user in a private fixture; only the ARM
# executable boundary and original-size/hash identities are modeled here.
for mode in ['normal', 'interrupted', 'wrong-result', 'wrong-original', 'wrong-version']:
    f = CASES / ('prepare-' + mode)
    for directory in [f / 'ebrmain/cramfs/lib', f / 'ebrmain/config', f / 'mnt/ext1', f / 'package']:
        directory.mkdir(parents=True, exist_ok=True)
    (f / 'ebrmain/.version').write_text('ver=6.11.2001\n' if mode != 'wrong-version' else 'ver=6.5.1383\n')
    (f / 'ebrmain/config/device.cfg').write_text('model=Pocket632\nvariant=U632\n')
    canonical = f / 'ebrmain/cramfs/lib/libopds_app_lib.so'
    canonical.write_bytes(b'wrong' if mode == 'wrong-original' else ORIGINAL)
    (f / 'expected').write_bytes(PATCHED)
    source = sub_hashes((ROOT / 'src/installer/common/prepare-library.sh').read_text(encoding='utf-8'))
    source = source.replace('= 598364', '= ' + str(len(ORIGINAL))).replace('= 610748', '= ' + str(len(PATCHED)))
    source = re.sub(r'/ebrmain|/mnt/ext1', lambda m: f.as_posix() + m[0], source)
    source = source.replace('"$package/tools/opds-patcher"', 'patcher_fixture')
    fake = '''
flock() { return 0; }
sync() { return 0; }
patcher_fixture() {
    echo called >> '__F__/patcher-calls'
    if [ '__MODE__' = interrupted ]; then echo torn > "$4"; return 130; fi
    if [ '__MODE__' = wrong-result ]; then echo wrong > "$4"; return 0; fi
    cp '__F__/expected' "$4"
}
'''.replace('__F__', f.as_posix()).replace('__MODE__', mode)
    helper = f / 'helper.sh'
    helper.write_text(fake + source, encoding='utf-8', newline='\n')
    wrapper = f / 'run.sh'
    wrapper.write_text('. "$1"\nprepare_library "$2" "$3" || exit 1\n', encoding='ascii')
    target_dir = f / 'package/lib'
    shell(wrapper, helper, target_dir, f / 'package', expected=0 if mode == 'normal' else 1)
    check(canonical.read_bytes() == (b'wrong' if mode == 'wrong-original' else ORIGINAL), 'prepare-original-never-written:' + mode)
    output = target_dir / 'libopds_app_lib.so'
    if mode == 'normal':
        shell(wrapper, helper, target_dir, f / 'package')
        check(output.read_bytes() == PATCHED and (f / 'patcher-calls').read_text().splitlines() == ['called'], 'root-free-cache-created-once-and-reused')
        output.write_bytes(b'damaged mapped cache')
        shell(wrapper, helper, target_dir, f / 'package', expected=1)
        check(output.read_bytes() == b'damaged mapped cache', 'damaged-cache-never-overwritten-while-potentially-mapped')
    else:
        check(not output.exists() and not list(target_dir.glob('.patch.*')), 'prepare-failure-no-partial-final-output:' + mode)

# Exact external-component checks (synthetic identities at this OS boundary).
for mode in ['missing', 'wrong-su', 'wrong-jailbreak', 'good', 'bundled-local']:
    f = CASES / ('external-pbjb-' + mode)
    package = f / 'package'
    external = f / 'components'
    package.mkdir(parents=True)
    external.mkdir()
    if mode != 'missing':
        (external / 'su').write_bytes(b'foreign' if mode == 'wrong-su' else SU)
        (external / 'jailbreak').write_bytes(b'foreign' if mode == 'wrong-jailbreak' else JAILBREAK)
    if mode == 'bundled-local':
        (package / 'pbjb').mkdir()
        (package / 'pbjb/su').write_bytes(SU)
        (package / 'pbjb/jailbreak').write_bytes(JAILBREAK)
    code = sub_hashes((ROOT / 'src/installer/common/pbjb-components.sh').read_text(encoding='utf-8'))
    code = code.replace('/mnt/ext1/system/opds-pbjb/8f1fb889d575237f2b292e88df6aabf552142d87', external.as_posix())
    script = f / 'probe.sh'
    script.write_text(code + '\nopds_get_pbjb "$1"\n', encoding='utf-8')
    shell(script, package, expected=0 if mode in ['good', 'bundled-local'] else 1)
    if mode in ['good', 'bundled-local']:
        check((package / 'pbjb/su').read_bytes() == SU and (package / 'pbjb/jailbreak').read_bytes() == JAILBREAK, 'verified-component-copy:' + mode)
    else:
        check(not (package / 'pbjb').exists(), 'external-components-refused-before-copy:' + mode)

# Real i18n shell with the stock iv2sh successful exit=1 convention.
i18n = ROOT / 'src/installer/common/i18n.sh'
probe = CASES / 'language.sh'
probe.write_text('iv2sh() { printf "%s\\n" "$VALUE"; return 1; }\n. "$1"\nVALUE=$2\nopds_select_language\necho "$OPDS_UI_LANGUAGE"\nopds_text cancel\n', encoding='ascii')
for value, language in [('ru', 'ru'), ('RU', 'ru'), ('ru_RU.UTF-8', 'ru'), ('ru-RU', 'ru'), ('en', 'en'), ('de', 'en'), ('', 'en')]:
    p = shell(probe, i18n, value)
    check(p.stdout.splitlines()[0] == language, 'native-read-exit1-language:' + repr(value))

dictionary = i18n.read_text(encoding='utf-8')
ru = dict(re.findall(r"ru/([a-z_]+)\) printf '%s\\n' '([^']*)';;", dictionary))
en = dict(re.findall(r"\*/([a-z_]+)\) printf '%s\\n' '([^']*)';;", dictionary))
check(ru.keys() == en.keys() and len(ru) >= 43, 'all-dialogs-have-RU-and-EN-pairs')
check(all(re.search('[\u0400-\u04ff]', text) for text in ru.values()) and '???' not in dictionary, 'Russian-translations-preserve-Unicode')

# Actual RU/EN UI dispatch and explicit cancellation of existing-root removal.
for policy in ['keep', 'remove']:
    for language in ['ru', 'en']:
        for action in ['install', 'uninstall', 'cancel-existing-root']:
            if action == 'cancel-existing-root' and policy != 'remove': continue
            f = CASES / ('ui-' + policy + '-' + language + '-' + action)
            userdir = f / ('mnt/ext1/system/.opds-authors-611-open-rooted' if policy == 'keep' else 'mnt/ext1/system/.opds-authors-611-open')
            cache = userdir / 'run.Ab12Cd'
            for directory in [cache / 'scripts', f / 'ebrmain/config', f / 'ebrmain/lib', f / 'ebrmain/cramfs/lib', f / 'mnt/secure']:
                directory.mkdir(parents=True, exist_ok=True)
            (f / 'ebrmain/.version').write_text('ver=6.11.2001\n')
            (f / 'ebrmain/config/device.cfg').write_text('model=Pocket632\nvariant=U632\n')
            (f / 'ebrmain/cramfs/lib/libopds_app_lib.so').write_bytes(ORIGINAL)
            (f / 'ebrmain/lib/libopds_app_lib.so').write_bytes(PATCHED if action == 'uninstall' else ORIGINAL)
            (f / 'mnt/secure/su').write_bytes(SU)
            (cache / 'scripts/i18n.sh').write_bytes(i18n.read_bytes())
            (cache / 'scripts/prepare-library.sh').write_text('prepare_library() { return 0; }\n')
            code = sub_hashes((ROOT / 'src/installer' / policy / 'oneapp-ui.sh').read_text(encoding='utf-8'))
            code = re.sub(r'/mnt/ext1|/mnt/secure|/var/tmp|/ebrmain|/proc', lambda m: f.as_posix() + m[0], code)
            code = code.replace('[ ! -x "$ROOT_HELPER" ]', '[ ! -f "$ROOT_HELPER" ]')
            code = code.replace('case "$CACHE" in "$USERDIR"/run.*) rm -rf "$CACHE";; esac', ': # cannot unlink running Windows script')
            code = code.replace('"$ROOT_HELPER" /bin/sh', 'root_fixture /bin/sh')
            cancel = '2' if action == 'cancel-existing-root' else '1'
            mocks = '''
dialog() { printf '%s\\n' "$*" >> '__F__/dialogs'; return __CANCEL__; }
root_fixture() { echo "$*" >> '__F__/root-calls'; }
iv2sh() { if [ "$1" = ReadConfig ]; then echo '__LANG__'; return 1; fi; }
flock() { return 0; }
id() { echo 'uid=101(reader)'; }
sync() { return 0; }
unset OPDS_UI_LANGUAGE
'''.replace('__F__', f.as_posix()).replace('__LANG__', language).replace('__CANCEL__', cancel)
            code = code.replace('umask 077\n', 'umask 077\n' + mocks, 1)
            script = cache / 'scripts/oneapp-ui.sh'
            script.write_text(code, encoding='utf-8', newline='\n')
            shell(script)
            if action == 'cancel-existing-root':
                check(not (f / 'root-calls').exists() and not (userdir / 'pending').exists(), 'cancel-existing-root-is-effective:' + language)
            else:
                check('stage ' + action in (f / 'root-calls').read_text(), 'localized-ui-dispatch:' + policy + ':' + language + ':' + action)

# Full SFX extraction, verification and RU->EN change using the same existing
# cache, with only the launch entry replaced by a harmless shell stub.
f = CASES / 'complete-sfx'
for directory in [f / 'ebrmain/config', f / 'mnt/ext1/system']:
    directory.mkdir(parents=True, exist_ok=True)
(f / 'ebrmain/.version').write_text('ver=6.11.2001\n')
(f / 'ebrmain/config/device.cfg').write_text('model=Pocket632\nvariant=U632\n')
header, members = apps['none']
safe = dict(members)
safe['scripts/standalone.sh'] = ('. "$(dirname -- "$0")/i18n.sh"\nopds_text cancel >> "' + f.as_posix() + '/executed"\n').encode()
safe['SHA256SUMS'] = ''.join(hashlib.sha256(b).hexdigest() + '  ' + n + '\n' for n, b in sorted(safe.items()) if n != 'SHA256SUMS').encode()
raw = io.BytesIO()
with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as archive:
    for n, b in sorted(safe.items()):
        item = tarfile.TarInfo(n); item.size = len(b); item.mode = 0o755
        archive.addfile(item, io.BytesIO(b))
compressed = builder['stored_gzip'](raw.getvalue())
old_compressed = (ROOT / 'dist/Online libraries.app').read_bytes().split(b'__OPDS_DATA__\n', 1)[1]
code = header.decode().replace(hashlib.sha256(old_compressed).hexdigest(), hashlib.sha256(compressed).hexdigest())
code = code.replace(hashlib.sha256(members['SHA256SUMS']).hexdigest(), hashlib.sha256(safe['SHA256SUMS']).hexdigest())
code = code.replace('/ebrmain', f.as_posix() + '/ebrmain').replace('/mnt/ext1', f.as_posix() + '/mnt/ext1')
code = code.replace('exec /bin/sh', "exec '" + HOST.as_posix() + "' sh")
mocks = '''
uname() { echo armv7l; }
iv2sh() { cat '__F__/locale'; return 1; }
dialog() { echo "$*" >> '__F__/dialogs'; return 1; }
flock() { return 0; }
OPDS_UI_LANGUAGE=ru
'''.replace('__F__', f.as_posix())
code = code.replace('umask 077\n', 'umask 077\n' + mocks, 1)
app = f / 'Online libraries.app'
app.write_bytes(code.encode() + b'__OPDS_DATA__\n' + compressed)
for language in ['ru', 'en']:
    (f / 'locale').write_text(language + '\n')
    shell(app)
check((f / 'executed').read_text(encoding='utf-8').splitlines() == ['\u041e\u0442\u043c\u0435\u043d\u0430', 'Cancel'], 'complete-SFX-and-existing-cache-language-switch')
check((f / 'mnt/ext1/system/.opds-authors-611-open/standalone-open-v9').is_dir(), 'new-cache-independent-of-universal-v8')

receipt = {'scope': __doc__, 'platform': sys.platform, 'checks': len(results), 'results': results,
           'private_reference': private, 'transaction_invocations': len(transaction.results),
           'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted((ROOT / 'src').rglob('*')) if p.is_file()}}
(ROOT / 'build/test-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('OFFLINE CHECKS PASSED:', len(results), '; transaction invocations:', len(transaction.results), '; private reference:', private['performed'])
