"""Build preflight/error regression tests; no network, compiler or ARM execution."""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('opds_build_under_test', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
import setup_tools
import get_pbjb

class BuildTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / '.cache/build-tests'
        directory.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.previous_cwd = Path.cwd()
        self.addCleanup(os.chdir, self.previous_cwd)
        self.env = patch.dict(os.environ)
        self.env.start()
        self.addCleanup(self.env.stop)
        for name in ['OPDS_ZIG', 'OPDS_BUSYBOX']:
            os.environ.pop(name, None)
        for module in [build, setup_tools, get_pbjb]:
            self.add_patch(module, 'ROOT', self.root)
        self.add_patch(build, 'LOG_PATH', None)
        for name in build.REQUIRED_SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# synthetic source marker\n', encoding='ascii')
        self.expected = {'jailbreak': b'synthetic jailbreak', 'su': b'synthetic su'}
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in self.expected.items()}
        self.add_patch(build, 'PBJB', hashes)
        self.add_patch(get_pbjb, 'FILES', hashes)
        self.add_patch(build.shutil, 'which', lambda name: None)

    def add_patch(self, obj, name, value):
        replacement = patch.object(obj, name, value)
        replacement.start()
        self.addCleanup(replacement.stop)

    def invoke(self, *args, auto=False):
        if not auto and '--setup' not in args:
            args = ('--offline', *args)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = build.cli(list(args))
        return status, output.getvalue()

    def ready(self):
        exe = self.root / '.tools/python/ziglang' / ('zig.exe' if os.name == 'nt' else 'zig')
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b'synthetic compiler, never executed')
        self.add_patch(build.subprocess, 'check_output', lambda *args, **kwargs: '0.13.0\n')
        for name, data in self.expected.items():
            path = self.root / 'external/pbjb' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def test_missing_components_reported_together_without_traceback(self):
        status, output = self.invoke('--test')
        self.assertNotEqual(status, 0)
        for text in ['Zig 0.13.0', 'external/pbjb/jailbreak', 'external/pbjb/su', 'setup', 'No compilation was started']:
            self.assertIn(text.lower(), output.lower())
        if os.name == 'nt':
            self.assertIn('Windows test shell', output)
        self.assertNotIn('Traceback', output)
        self.assertFalse((self.root / 'dist').exists())

    def test_check_never_downloads_even_with_setup_flag(self):
        with patch.object(setup_tools, 'setup_zig') as install, patch.object(get_pbjb, 'obtain_components') as get:
            status, _ = self.invoke('--check', '--setup')
        self.assertNotEqual(status, 0)
        install.assert_not_called()
        get.assert_not_called()

    def test_ready_check_does_not_compile(self):
        self.ready()
        with patch.object(build, 'compile_all') as compile_tool:
            status, output = self.invoke('--check')
        self.assertEqual(status, 0, output)
        compile_tool.assert_not_called()
        self.assertIn('Preflight passed', output)
        self.assertFalse((self.root / 'dist').exists())

    def test_external_mode_does_not_require_pbjb(self):
        self.ready()
        (self.root / 'external/pbjb/su').unlink()
        (self.root / 'external/pbjb/jailbreak').unlink()
        status, output = self.invoke('--check', '--external-pbjb')
        self.assertEqual(status, 0, output)

    def test_local_copy_still_requires_pbjb_in_external_mode(self):
        self.ready()
        (self.root / 'external/pbjb/su').unlink()
        status, output = self.invoke('--check', '--external-pbjb', '--local-pbjb')
        self.assertNotEqual(status, 0)
        self.assertIn('external/pbjb/su', output)

    def test_wrong_zig_version_is_actionable(self):
        self.ready()
        self.add_patch(build.subprocess, 'check_output', lambda *args, **kwargs: '0.14.0\n')
        status, output = self.invoke('--check')
        self.assertNotEqual(status, 0)
        self.assertIn('0.14.0', output)
        self.assertIn('OPDS_ZIG', output)
        self.assertNotIn('Traceback', output)

    def test_invalid_compiler_override_does_not_fall_back_silently(self):
        os.environ['OPDS_ZIG'] = str(self.root / 'missing-zig.exe')
        status, output = self.invoke('--check', '--external-pbjb')
        self.assertNotEqual(status, 0)
        self.assertIn('Zig cannot be used', output)

    def test_bad_pbjb_not_overwritten_or_downloaded(self):
        self.ready()
        path = self.root / 'external/pbjb/su'
        path.write_bytes(b'foreign component')
        with patch.object(get_pbjb, 'obtain_components') as get:
            status, output = self.invoke('--setup')
        self.assertNotEqual(status, 0)
        self.assertIn('SHA-256', output)
        self.assertEqual(path.read_bytes(), b'foreign component')
        get.assert_not_called()

    def test_missing_test_shell_stops_before_compilation(self):
        self.ready()
        with patch.object(build, 'compile_all') as compile_tool:
            status, output = self.invoke('--test')
        self.assertNotEqual(status, 0)
        compile_tool.assert_not_called()
        self.assertTrue('test shell' in output or 'POSIX' in output)

    def test_network_error_is_short_and_logged(self):
        with patch.object(setup_tools, 'setup_zig', side_effect=URLError('test connection refused')):
            status, output = self.invoke('--setup', '--external-pbjb')
        self.assertNotEqual(status, 0)
        self.assertIn('Zig setup failed', output)
        self.assertIn('network/proxy/certificates', output)
        self.assertNotIn('Traceback', output)
        self.assertIn('Traceback', (self.root / 'build/build.log').read_text(encoding='utf-8'))

    def test_debug_explicitly_enables_traceback(self):
        with patch.object(setup_tools, 'setup_zig', side_effect=URLError('test network')):
            status, output = self.invoke('--setup', '--external-pbjb', '--debug')
        self.assertNotEqual(status, 0)
        self.assertIn('Traceback', output)

    def test_command_failure_saved_to_log_without_console_traceback(self):
        self.ready()
        result = subprocess.CompletedProcess(['synthetic-tool'], 7, 'stdout details', 'compiler failure details')
        with patch.object(build.subprocess, 'run', return_value=result):
            status, output = self.invoke()
        self.assertNotEqual(status, 0)
        self.assertIn('exit code 7', output)
        self.assertNotIn('Traceback', output)
        self.assertIn('compiler failure details', (self.root / 'build/build.log').read_text(encoding='utf-8'))

    def test_missing_sources_are_named_before_compile(self):
        self.ready()
        (self.root / 'src/patcher/patcher.c').unlink()
        with patch.object(build, 'compile_all') as compile_tool:
            status, output = self.invoke()
        self.assertNotEqual(status, 0)
        self.assertIn('Incomplete source tree', output)
        compile_tool.assert_not_called()

    def test_existing_apps_preserved_on_preflight_failure(self):
        path = self.root / 'dist/Online libraries.app'
        path.parent.mkdir()
        path.write_bytes(b'previous working artifact')
        status, _ = self.invoke()
        self.assertNotEqual(status, 0)
        self.assertEqual(path.read_bytes(), b'previous working artifact')

    def test_logs_and_cache_settings_remain_local(self):
        self.ready()
        status, output = self.invoke('--check')
        self.assertEqual(status, 0, output)
        for name in ['TMP', 'TEMP', 'TMPDIR', 'ZIG_GLOBAL_CACHE_DIR', 'ZIG_LOCAL_CACHE_DIR', 'XDG_CACHE_HOME']:
            self.assertTrue(Path(os.environ[name]).is_relative_to(self.root), name)
        self.assertTrue(build.LOG_PATH.is_relative_to(self.root))

    def test_pbjb_missing_file_fetch_does_not_redownload_existing_valid_file(self):
        self.ready()
        (self.root / 'external/pbjb/su').unlink()
        response = io.BytesIO(self.expected['su'])
        with patch.object(get_pbjb.urllib.request, 'urlopen', return_value=response) as download:
            get_pbjb.obtain_components()
        self.assertEqual(download.call_count, 1)
        self.assertTrue(download.call_args.args[0].endswith('/su'))

    def test_old_python_is_rejected_cleanly(self):
        self.add_patch(build.sys, 'version_info', (3, 10, 0))
        status, output = self.invoke('--check')
        self.assertNotEqual(status, 0)
        self.assertIn('Python 3.11', output)
        self.assertNotIn('Traceback', output)

    def test_default_build_automatically_prepares_missing_inputs(self):
        sentinel = RuntimeError('stop after successful automatic preparation')
        def install():
            self.ready()
        with patch.object(setup_tools, 'setup_zig', side_effect=install) as zig_setup, \
             patch.object(get_pbjb, 'obtain_components') as pbjb_setup, \
             patch.object(build, 'compile_all', side_effect=sentinel):
            status, output = self.invoke(auto=True)
        zig_setup.assert_called_once()
        pbjb_setup.assert_called_once()
        self.assertIn('Ready to compile', output)
        self.assertNotEqual(status, 0)  # Deliberate stop before any real compiler.

if __name__ == '__main__':
    unittest.main()
