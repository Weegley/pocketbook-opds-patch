# Automatic build

**English** | [Русский](BUILD.ru.md)

Run the launcher in the repository root. **Python, Zig, pip, CMake and an ARM compiler do not need to be installed first.** No firmware/SDK/library is needed on the build computer.

## Windows 11 x86-64

From CMD or PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

The PowerShell launcher downloads the pinned official **portable CPython 3.14.2 ZIP**, verifies SHA-256 and unpacks it into `.tools/python-runtime/windows-3.14.2/`. It then uses that interpreter to prepare Zig/pbjb and build all three apps. No Python installer, registry changes, machine/user PATH edits, administrator rights, WSL or Docker are involved.

The ordinary build does not depend on a system Python, even if one is installed. Subsequent runs reuse the checked local runtime. An explicit advanced override remains available: `-Python C:\Path\To\python.exe` (Python 3.11+ with SSL).

## Debian/Ubuntu x86-64

```sh
sh build.sh
```

The shell launcher downloads pinned **CPython 3.14.2, python-build-standalone release 20251209**, verifies SHA-256 and extracts it under `.tools/python-runtime/linux-3.14.2-20251209/`. It does not call sudo, apt, pip or a system installer. System Python is not needed. An advanced explicit override is `PYTHON=/path/to/python3 sh build.sh`.

Base OS tools must be available: POSIX `sh`, `uname`, `tar`, `sha256sum`, `awk`, standard file utilities, and **curl or GNU wget** with working HTTPS certificates. These are bootstrap primitives: without any TLS downloader the shell cannot obtain a Python archive. GNU wget is invoked with `--no-config --no-hsts` to avoid configuration/HSTS writes in the user profile; curl configuration files are disabled. No system packages are installed by this project. Linux support targets glibc x86-64 (normal Debian/Ubuntu), not Alpine/musl or other architectures.

## What is downloaded

All versions, URLs and hashes are pinned in [python-bootstrap.lock](../scripts/python-bootstrap.lock), [dependencies.lock.json](../dependencies.lock.json) and [requirements-build.txt](../requirements-build.txt). There is no latest-version lookup.

| Dependency | Source | Local destination |
| --- | --- | --- |
| CPython 3.14.2 (Windows) | [official version manifest](https://www.python.org/ftp/python/3.14.2/windows-3.14.2.json), `python-3.14.2-amd64.zip` | `.tools/downloads/`, `.tools/python-runtime/` |
| CPython 3.14.2 (Linux) | [python-build-standalone 20251209](https://github.com/astral-sh/python-build-standalone/releases/tag/20251209), x86-64 GNU install-only stripped archive | `.tools/downloads/`, `.tools/python-runtime/` |
| Zig 0.13.0 | Hash-pinned [PyPI wheel](https://pypi.org/project/ziglang/0.13.0/) extracted without pip | `.tools/downloads/`, `.tools/python/ziglang/` |
| pbjb jailbreak/su | [exact commit and hashes](PBJB.md) | `external/pbjb/` |
| Windows test shell, only with `-Test` | [BusyBox-w64](https://frippery.org/busybox/), pinned SHA | `.tools/busybox64.exe` |

The Windows test-shell URL is mutable; a changed binary is refused. If the pinned shell is no longer served, obtain the exact upstream archive version recorded in `dependencies.lock.json`, or build without the optional test flag. It is never silently upgraded.

Bootstrap Python is extracted into a temporary staging directory and activated only after archive SHA and interpreter/SSL checks succeed. Interrupted downloads/extraction do not activate a partial runtime. Unexpected cached hashes, redirected tool paths or damaged runtimes are refused rather than overwritten blindly. Existing `.app` files are not changed when preflight fails.

## Outputs and containment

- `dist/`: `Online libraries.app`, `Non-rooted patch.app`, `Rooted patch.app`, `SHA256SUMS.txt`.
- `build/`: generated native tools/link-only stubs, reports and `build.log`.
- `.cache/`: compiler caches, temporary files, test models and `bootstrap.log` for failures before Python starts.
- `.tools/`, `external/`: downloaded/extracted dependencies.

**All these directories stay inside the project and are excluded from Git/source exports.** Tools are not installed globally or bundled into the source ZIP. PowerShell restores process environment settings on return. Compiler/XDG/temp caches are redirected to this project; Python bytecode writes are disabled. Linux may read the system CA bundle but does not modify it.

Zig compiles the ARM patcher and the original C/C++ launcher. Project-owned link-only declarations record the firmware ABI without needing firmware libraries at build time; the stub DSOs are not shipped. The launcher must match its recorded universal-v8 SHA or the build fails. All three apps exclude the proprietary OPDS library. Default Non-rooted embeds only the two exact pbjb binaries; see [PBJB.md](PBJB.md).

## Optional modes

```powershell
.\build.ps1 -Test             # bootstrap, build, full offline tests
.\build.ps1 -Check            # inspect only; never download or compile
.\build.ps1 -Check -Test      # also inspect optional test dependencies
.\build.ps1 -Offline          # build using only cached inputs
.\build.ps1 -DebugBuild       # include console tracebacks on failure
.\build.ps1 -ExternalPbjb     # omit pbjb from Non-rooted; external reader files required
```

```sh
sh build.sh test
sh build.sh --check
sh build.sh --offline
sh build.sh --debug
sh build.sh --external-pbjb
```

`-Setup` / `--setup` remains a compatibility alias; it is no longer required. `-Check`/`--check` and offline mode never download **even if Python is absent**. The check then reports the missing local interpreter and exits nonzero. `OPDS_ZIG` can explicitly select an existing Zig 0.13.0; otherwise the downloaded local compiler is used. `-LocalPbjb` additionally writes the legacy `dist-local/` output.

If a build fails, the console identifies the component/stage and points to its log. Wrong versions/SHA are not bypassed. For network failures, check connectivity, proxy and certificates; a verified pinned archive can also be placed in `.tools/downloads/` for offline extraction. Logs stay in the project.

## Verify and test

```powershell
Get-FileHash -Algorithm SHA256 .\dist\*.app
Get-Content .\dist\SHA256SUMS.txt
```

```sh
(cd dist && sha256sum -c SHA256SUMS.txt)
```

Full `-Test`/`--test` runs native patcher/callback models, build preflight tests, synthetic Python-bootstrap tests, archive checks and actual installer shell control flow against modeled Linux boundaries. No ARM firmware, exploit or real mount is executed on the computer. Windows uses its pinned BusyBox; Linux uses `/bin/sh` and standard POSIX tools. Full shell models require a project path without whitespace; app compilation/packaging supports spaces. Test reports are generated under `build/`.

To run just the fast build/bootstrap checks with an available Python: `python -B tests/test_build.py` and `python -B tests/test_bootstrap.py`. Bootstrap tests substitute downloads/interpreter boundaries using synthetic archives; they are not evidence of a completed real Linux bootstrap.

An optional private reference comparison uses `OPDS_ORIGINAL` and `OPDS_REFERENCE`, pointing to the owner's exact library/reference **outside this repository**. Comparison is in memory and no proprietary fixture is written. Those files are not required for public builds/tests.

Tar/gzip packaging is deterministic. The owner confirmed the automatic builds on **Windows and Linux**, as well as all three apps on the reader. [VALIDATION.md](VALIDATION.md) records this separately from agent-run tests and historical environment/network limits.

## Export for GitHub

With the local Python (Windows path shown; Linux uses the pinned runtime's `python/bin/python3`):

```powershell
.\.tools\python-runtime\windows-3.14.2\python.exe -I -B scripts/export_source.py
.\.tools\python-runtime\windows-3.14.2\python.exe -I -B scripts/export_release.py
```

`COMMIT_FILES.txt` is the exact source allowlist; the source ZIP contains only those text files. Never commit `.tools/`, `.cache/`, `external/`, compiled artifacts or firmware. The app release ZIP contains the allowlisted sources plus the three apps; the proprietary library is absent from both.
