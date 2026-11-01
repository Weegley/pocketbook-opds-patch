"""Run actual one-app shell control flow with modeled Linux boundaries on Windows.

No ARM code or privilege escalation is executed. Reboot, UID, lstat, immutable
flags, symlinks, mounts and flock are models, not device/crash-consistency tests.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

import model_physical
from model_support import ROOT as BASE, SU, sub_hashes
old=vars(model_physical)
HOST=old['HOST']; require=old['require']; ORIGINAL=old['ORIGINAL']; PATCHED=old['PATCHED']
POLICY='keep'
HERE=BASE / 'src/installer' / POLICY
results=[]

def make(name):
    f, manager = old["make"]("oneapp-" + name)
    core = manager.with_name("opds-system.sh")
    code = core.read_text()
    code = re.sub(r"^BASE=.*$", 'BASE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)', code, flags=re.M)
    code = code.replace("*/opds-authors-6.11)", "*/opds-authors-6.11|*/oneapp-runtime)")
    code = code.replace("*/00-opds-physical-b.sh)", "*/00-opds-physical-b.sh|*/00-opds-oneapp-611.sh)")
    code = code.replace("*/secure/su) echo", "*/secure/su) echo")
    code += "\n"  # Boundary functions are inserted before action dispatch, not after it.
    boundary = r'''
chattr() { echo "$*" >> '__F__/chattr-calls'; [ ! -e '__F__/fail-chattr' ]; }
model_reboot() { echo reboot >> '__F__/reboot-calls'; }
'''.replace("__F__", f.as_posix())
    code = code.replace("\numask 077", "\n" + boundary + "\numask 077", 1)
    # Inject failures at the real payload-copy boundary after the protected job
    # was staged, rather than changing installer control flow.
    code = re.sub(r"(?m)^    if \[ -e '[^']+/fail-copy' \].*$", lambda _: '    if [ -e "' + f.as_posix() + '/fail-copy" ]; then case "${1:-}" in */payload/libopds_app_lib.so) return 1;; esac; fi', code)
    core.write_text(code, encoding="utf-8", newline="\n")
    script = sub_hashes((HERE / "oneapp-root.sh").read_text(encoding="utf-8"))
    paths = ["/mnt/secure", "/mnt/ext1", "/ebrmain", "/proc"]
    script = re.sub("|".join(re.escape(p) for p in paths), lambda m: f.as_posix() + m[0], script)
    script = re.sub(r"\[\s+(!\s+)?-L\s+([^\]]+?)\s*\]", lambda m: ("! " if m[1] else "") + "is_link " + m[2], script)
    script = re.sub(r"(?m)^(\s*)(if )?/bin/sh ", lambda m: m[1] + (m[2] or "") + "'" + HOST.as_posix() + "' sh ", script)
    for command in ["chmod", "cp", "chown", "chattr", "rm"]:
        script = script.replace("/bin/" + command + " ", command + " ")
    script = script.replace("/sbin/reboot", "model_reboot")
    target = core.with_name("oneapp-root.sh")
    target.write_text(script, encoding="utf-8", newline="\n")
    (f / "mnt/secure/su").write_bytes(SU)
    (f / "package/pbjb").mkdir()
    (f / "package/pbjb/su").write_bytes(SU)
    public_cache = '.opds-authors-611-open-rooted' if POLICY == 'keep' else '.opds-authors-611-open'
    (f / 'mnt/ext1/system' / public_cache).mkdir(parents=True)
    with (f / "proc/mounts").open("a") as stream:
        stream.write(f"/dev/user_int {f.as_posix()}/mnt/ext1 vfat rw,nosuid,nodev 0 0\n")
    with (f / "proc/self/mountinfo").open("a") as stream:
        stream.write(f"4 1 179:1 / {f.as_posix()}/mnt/ext1 rw - vfat /dev/user_int rw\n")
    return f, target


def call(f, script, *args, expected=0):
    process = subprocess.run([str(HOST), "sh", str(script), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    logs = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted((f / "mnt/secure/opds-authors-6.11").glob("oneapp-*-boot.log.*")))
    require(process.returncode == expected, f"{f.name}: {args} expected {expected}, got {process.returncode}\n{process.stdout}{process.stderr}\n{logs}")
    results.append({"fixture": f.name, "args": args, "exit": process.returncode})
    (f / f"oneapp-call-{len(results)}.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    return process


def boot(f, expected=0):
    proc = f / "proc/123"
    if proc.exists():
        shutil.rmtree(proc)
    script = f / "mnt/secure/opds-authors-6.11/oneapp-runtime/scripts/oneapp-root.sh"
    return call(f, script, "boot", expected=expected)


def state(f, name="oneapp-phase"):
    return (f / "mnt/secure/opds-authors-6.11" / name).read_text().strip()


def target(f):
    return f / "ebrmain/lib/libopds_app_lib.so"


def completed(f, action):
    require(state(f) == "complete", "Completion state missing")
    require(not (f / "mnt/secure/su").exists(), "Root helper retained on success")
    require(not list((f / "mnt/secure/runonce").glob("*.sh")), "Root-dependent boot hook retained")
    require("ext2 ro,relatime,errors=remount-ro" in (f / "proc/mounts").read_text(), "System mount is not read-only")
    require((f / "ebrmain/cramfs/lib/libopds_app_lib.so").read_bytes() == ORIGINAL, "SquashFS source modified")
    require((f / f"mnt/ext1/OPDS_Authors_611_{action}.log").exists(), "Boot log was not exported")


