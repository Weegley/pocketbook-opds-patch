"""Portable-Python bootstrap tests with synthetic archives, never downloads."""
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ.get('OPDS_BUSYBOX') or str(ROOT / ('.tools/busybox64.exe' if os.name == 'nt' else '.tools/posix-tools')))

def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"

class WindowsBootstrapTests(unittest.TestCase):
    def setUp(self):
        if os.name != 'nt':
            self.skipTest('Native PowerShell bootstrap checks require Windows')
        cache = ROOT / '.cache/bootstrap-tests'
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/bootstrap-python.ps1', self.root / 'scripts/bootstrap-python.ps1')

    def prepare(self, mode='normal'):
        archive = self.root / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('python.exe', 'synthetic placeholder, never executed')
            if mode == 'unsafe':
                z.writestr('../escape.txt', 'must not be written')
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (self.root / 'scripts/python-bootstrap.lock').write_text(
            'VERSION=3.14.2\nWINDOWS_URL=https://invalid.invalid/test-python.zip\n'
            'WINDOWS_ARCHIVE=test-python.zip\nWINDOWS_SHA256=' + digest + '\n'
            'WINDOWS_INSTALL=windows-3.14.2\nWINDOWS_EXE=python.exe\n', encoding='ascii')
        return archive

    def invoke(self, body, mode='normal'):
        script = self.root / 'harness.ps1'
        fake_probe = '$false' if mode == 'probe-fails' else '(Test-Path -LiteralPath $Executable)'
        script.write_text("""$ErrorActionPreference = 'Stop'
$root = __ROOT__
. (Join-Path $root 'scripts/bootstrap-python.ps1')
$script:downloads = 0
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec)
    $script:downloads++
    if ('__MODE__' -eq 'network-fails') { throw 'simulated network failure' }
    Copy-Item -LiteralPath (Join-Path $root 'fixture.zip') -Destination $OutFile
}
function Test-BuildPython {
    param($Executable, $ExactVersion)
    return __PROBE__
}
try {
__BODY__
} catch {
    Write-Output ('EXPECTED_ERROR=' + $_.Exception.Message)
}
Write-Output ('DOWNLOADS=' + $script:downloads)
""".replace('__ROOT__', ps_quote(self.root)).replace('__MODE__', mode)
            .replace('__PROBE__', fake_probe).replace('__BODY__', body), encoding='utf-8')
        p = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def test_download_extract_and_cache_reuse(self):
        self.prepare()
        out = self.invoke('$first = Get-ProjectPython -Root $root\n$second = Get-ProjectPython -Root $root\nif ($first -ne $second) { throw "Different cached paths" }')
        self.assertNotIn('EXPECTED_ERROR=', out)
        self.assertIn('DOWNLOADS=1', out)
        self.assertTrue((self.root / '.tools/python-runtime/windows-3.14.2/python.exe').is_file())

    def test_check_does_not_download_python(self):
        self.prepare()
        out = self.invoke('Get-ProjectPython -Root $root -NoDownload')
        self.assertIn('Check/offline mode does not download', out)
        self.assertIn('DOWNLOADS=0', out)

    def test_network_failure_does_not_activate_runtime(self):
        self.prepare()
        out = self.invoke('Get-ProjectPython -Root $root', 'network-fails')
        self.assertIn('simulated network failure', out)
        self.assertFalse((self.root / '.tools/python-runtime/windows-3.14.2').exists())

    def test_wrong_cached_hash_not_extracted_or_overwritten(self):
        self.prepare()
        archive = self.root / '.tools/downloads/test-python.zip'
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b'foreign archive')
        out = self.invoke('Get-ProjectPython -Root $root')
        self.assertIn('SHA-256 mismatch', out)
        self.assertIn('DOWNLOADS=0', out)
        self.assertEqual(archive.read_bytes(), b'foreign archive')

    def test_wrong_download_hash_never_activates_runtime(self):
        archive = self.prepare()
        archive.write_bytes(b'corrupted download')
        out = self.invoke('Get-ProjectPython -Root $root')
        self.assertIn('download SHA-256 mismatch', out)
        self.assertFalse((self.root / '.tools/python-runtime/windows-3.14.2').exists())

    def test_bootstrap_inside_project_path_with_spaces(self):
        previous = self.root
        self.root = previous / 'project with spaces'
        (self.root / 'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/bootstrap-python.ps1', self.root / 'scripts/bootstrap-python.ps1')
        self.prepare()
        out = self.invoke('Get-ProjectPython -Root $root')
        self.assertNotIn('EXPECTED_ERROR=', out)
        self.assertTrue((self.root / '.tools/python-runtime/windows-3.14.2/python.exe').exists())

    def test_zip_traversal_refused_and_stage_cleaned(self):
        self.prepare('unsafe')
        out = self.invoke('Get-ProjectPython -Root $root')
        self.assertIn('Unsafe Python ZIP path', out)
        self.assertFalse((self.root / '.tools/python-runtime/escape.txt').exists())
        self.assertFalse(list((self.root / '.tools/python-runtime').glob('.install-*')))

    def test_failed_interpreter_probe_never_activates_partial_install(self):
        self.prepare()
        out = self.invoke('Get-ProjectPython -Root $root', 'probe-fails')
        self.assertIn('failed its version/SSL check', out)
        self.assertFalse((self.root / '.tools/python-runtime/windows-3.14.2').exists())
        self.assertFalse(list((self.root / '.tools/python-runtime').glob('.install-*')))

    def test_path_outside_project_refused(self):
        self.prepare()
        out = self.invoke('Assert-ProjectPath $root (Join-Path (Split-Path $root -Parent) "outside")')
        self.assertIn('must stay inside', out)
        self.assertIn('DOWNLOADS=0', out)

class ShellBootstrapTests(unittest.TestCase):
    def setUp(self):
        if not HOST.is_file():
            self.skipTest('OS-boundary shell model needs the local test shell/adapter')
        cache = ROOT / '.cache/bootstrap-tests'
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'scripts').mkdir()

    def model(self, mode='normal'):
        content = b'synthetic interpreter placeholder, not an executable'
        archive = self.root / 'fixture.tar.gz'
        with tarfile.open(archive, 'w:gz') as t:
            info = tarfile.TarInfo('python/bin/python3')
            info.size = len(content)
            t.addfile(info, io.BytesIO(content))
        pins = ('VERSION=3.14.2\nLINUX_URL=https://invalid.invalid/test.tar.gz\n'
                'LINUX_ARCHIVE=test.tar.gz\nLINUX_SHA256=' + hashlib.sha256(archive.read_bytes()).hexdigest() + '\n'
                'LINUX_INSTALL=linux-3.14.2-test\nLINUX_EXE=python/bin/python3\n')
        (self.root / 'scripts/python-bootstrap.lock').write_text(pins, encoding='ascii')
        # Only the native interpreter and tar OS boundaries are substituted.
        helper = self.root / 'tar_model.py'
        helper.write_text("""import sys,tarfile
if sys.argv[1]=='-tzf':
    with tarfile.open(sys.argv[2]) as a:
        print('\\n'.join(a.getnames()))
else:
    with tarfile.open(sys.argv[2]) as a:
        a.extractall(sys.argv[4],filter='data')
""", encoding='ascii')
        mocks = """
uname() { case "$1" in -s) echo Linux;; -m) echo x86_64;; esac; }
curl() {
    echo call >> '__F__/network-calls'
    if [ '__MODE__' = network-fails ]; then return 1; fi
    while [ "$#" -gt 0 ]; do
        if [ "$1" = --output ]; then shift; cp '__F__/fixture.tar.gz' "$1"; return; fi
        shift
    done
    return 1
}
tar() { '__PY__' -I -B '__F__/tar_model.py' "$@"; }
fake_python() {
    for argument do case "$argument" in *'print(sys.version.split()'*) echo 3.14.2;; esac; done
    return 0
}
""".replace('__F__', self.root.as_posix()).replace('__MODE__', mode).replace('__PY__', Path(sys.executable).as_posix())
        code = (ROOT / 'build.sh').read_text(encoding='utf-8')
        code = code.replace('set -eu\n', 'set -eu\n' + mocks, 1)
        code = code.replace('"$1" -I -B -c', 'fake_python "$1" -I -B -c')
        code = code.replace('"$stage/$LINUX_EXE" -I -B -c', 'fake_python "$stage/$LINUX_EXE" -I -B -c')
        code = code.replace('"$python_bin" -I -B -c', 'fake_python "$python_bin" -I -B -c')
        code = code.replace('exec "$python_bin" -I -B scripts/build.py "$@"', 'echo BUILD_DISPATCHED\nexit 0')
        script = self.root / 'build.sh'
        script.write_text(code, encoding='utf-8', newline='\n')
        return script

    def invoke(self, script, *args):
        env = os.environ.copy()
        env.pop('PYTHON', None)
        return subprocess.run([str(HOST), 'sh', str(script), *args], env=env, capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=30)

    def test_linux_control_flow_download_extract_and_reuse(self):
        script = self.model()
        first = self.invoke(script)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = self.invoke(script)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual((self.root / 'network-calls').read_text().splitlines(), ['call'])
        self.assertTrue((self.root / '.tools/python-runtime/linux-3.14.2-test/python/bin/python3').is_file())

    def test_linux_check_and_offline_modes_never_download(self):
        script = self.model()
        for flag in ['--check', '--offline']:
            result = self.invoke(script, flag)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.root / 'network-calls').exists())

    def test_linux_failed_download_never_activates_runtime(self):
        script = self.model('network-fails')
        result = self.invoke(script)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / '.tools/python-runtime/linux-3.14.2-test').exists())

    def test_linux_wrong_download_hash_is_refused(self):
        script = self.model()
        (self.root / 'fixture.tar.gz').write_bytes(b'corrupted download')
        result = self.invoke(script)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SHA-256 mismatch', result.stderr)
        self.assertFalse((self.root / '.tools/python-runtime/linux-3.14.2-test').exists())

if __name__ == '__main__':
    unittest.main()
