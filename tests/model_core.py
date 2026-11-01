"""Execute installer control flow in native Windows ash with simulated Linux OS calls.

Only a rewritten copy under evidence/host-tests is executed. No ARM code, Linux
mount, device, production system path, or privilege escalation is executed.
Windows cannot create Linux symlinks here: LINK: files model only that OS boundary.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from model_support import ROOT as B, HOST, CASES, ORIGINAL, PATCHED, sub_hashes, MemoryFile
ROOT = CASES / 'core'
ROOT.mkdir(parents=True, exist_ok=True)
original = MemoryFile(ORIGINAL)
payload = MemoryFile(PATCHED)
source = sub_hashes((B / 'src/installer/common/opds-system.sh').read_text(encoding='utf-8'))
results = []

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def fixture(name):
    f = ROOT / name
    for p in ['ebrmain/lib', 'ebrmain/cramfs/lib', 'ebrmain/config', 'mnt/secure', 'proc/self', 'proc/123', 'sys/class/block/mmcblk0', 'sys/class/block/mmcblk0p8', 'package/scripts', 'package/payload']:
        (f / p).mkdir(parents=True, exist_ok=True)
    def put(path, value):
        (f/path).write_text(value, encoding='utf-8', newline='\n')
    put('ebrmain/.version', 'ver=6.11.2001\n')
    put('ebrmain/config/device.cfg', 'model=Pocket632\nvariant=U632\n')
    put('ebrmain/lib/libopds_app_lib.so', 'LINK:../cramfs/lib/libopds_app_lib.so\n')
    (f/'ebrmain/cramfs/lib/libopds_app_lib.so').write_bytes(original.read_bytes())
    (f/'package/payload/libopds_app_lib.so').write_bytes(payload.read_bytes())
    for p in ['sys/class/block/mmcblk0/ro','sys/class/block/mmcblk0p8/ro']:
        put(p,'0\n')
    put('free','10000\n');put('uid','0\n')
    put('device-dir','dev\n')
    put('secure-meta','102:102:drwxrwx---\n')
    put('helper-result','0\n')
    prefix=f.as_posix()
    mounts=f'{prefix}/dev/ebrmain {prefix}/ebrmain ext4 ro,relatime 0 0\n{prefix}/dev/secure {prefix}/mnt/secure ext4 rw,relatime 0 0\n/dev/loop0 {prefix}/ebrmain/cramfs squashfs ro,relatime 0 0\n'
    put('proc/mounts', mounts)
    put('proc/self/mountinfo',f'1 0 179:8 / {prefix}/ebrmain ro - ext4 {prefix}/dev/ebrmain ro\n2 0 179:9 / {prefix}/mnt/secure rw - ext2 {prefix}/dev/secure rw\n')
    put('proc/123/maps', f'93000-94000 r-xp 00093000 b3:08 777 {prefix}/ebrmain/lib/libopds_app_lib.so\n')
    rewritten=source
    paths=['/dev/mmcblk0p8','/dev/mmcblk0p9','/dev/ebrmain','/dev/secure','/mnt/secure','/sys/class/block','/usr/lib','/ebrmain','/proc']
    rewritten=re.sub('|'.join(re.escape(p) for p in paths),lambda m:prefix+m[0],rewritten)
    rewritten=re.sub(r'^BASE=.*$', f"BASE='{prefix}/package'",rewritten,flags=re.M)
    # Model only OS lstat/readlink/uid/perms/mount. The installer branch/backup/rename/hash code stays intact.
    rewritten=re.sub(r'\[\s+(!\s+)?-L\s+([^\]]+?)\s*\]',lambda m:('! ' if m[1] else '')+'is_link '+m[2],rewritten)
    meta='metadata() { case "$1" in */opds-authors-6.11) echo 0:0:drwx------;; */ebrmain/lib|*/runonce) echo 0:0:drwxr-xr-x;; */mnt/secure) bb cat "'+prefix+'/secure-meta";; */secure/su) echo 0:0:-rwsr-xr-x;; */00-opds-authors-once.sh) echo 0:0:-rwxr-xr-x;; *) echo 0:0:-rw-r--r--;; esac; }'
    rewritten=re.sub(r'^metadata\(\).*$',lambda m:meta,rewritten,flags=re.M)
    wrappers='\n'.join(f'{n}() {{ bb {n} "$@"; }}' for n in ['awk','cat','grep','readlink','sha256sum','mkdir','rmdir','rm','mv','cp','chmod','ln','ls','wc','tr','mktemp'])
    mocks=r'''
bb() { '__HOST__' "$@"; }
__WRAPPERS__
is_link() { [ -f "$1" ] && [ "$(bb head -c 5 "$1")" = LINK: ]; }
id() { bb cat '__FIXTURE__/uid'; }
su() { bb cat '__FIXTURE__/helper-result'; }
readlink() {
    for p in "$@"; do :; done
    case "$p" in
      */dev/ebrmain|*/dev/mmcblk0p8) echo "__FIXTURE__/$(bb cat '__FIXTURE__/device-dir')/mmcblk0p8";;
      */dev/secure|*/dev/mmcblk0p9) echo "__FIXTURE__/$(bb cat '__FIXTURE__/device-dir')/mmcblk0p9";;
      */usr/lib) echo '__FIXTURE__/ebrmain/lib';;
      */proc/123/exe) echo '__FIXTURE__/ebrmain/cramfs/bin/sreader/explorer-3';;
      */proc/*/ns/mnt) echo 'mnt:[1]';;
      *) if is_link "$p"; then
             if [ "$1" = -f ]; then echo '__FIXTURE__/ebrmain/cramfs/lib/libopds_app_lib.so';
             else bb cut -c 6- "$p"; fi
         else return 1; fi;;
    esac
}
sha256sum() {
    if is_link "$1"; then bb sha256sum '__FIXTURE__/ebrmain/cramfs/lib/libopds_app_lib.so';
    else bb sha256sum "$@"; fi
}
cat() {
    if [ -e '__FIXTURE__/fail-copy' ] && [ "${1:-}" = '__FIXTURE__/package/payload/libopds_app_lib.so' ]; then return 1; fi
    bb cat "$@"
}
rm() {
    if [ -e '__FIXTURE__/fail-rm' ]; then
        for p in "$@"; do case "$p" in */.libopds_app_lib.so.new.*) return 1;; esac; done
    fi
    bb rm "$@"
}
ls() {
    if [ "$1" = -ldn ] && is_link "$2"; then echo "lrwxrwxrwx 1 1000 1000 32 Jan 1 00:00 $2";
    elif [ "$1" = -Lid ]; then echo "777 $2";
    else bb ls "$@"; fi
}
chown() { return 0; }
ln() { [ "$1" = -s ] || return 1; [ ! -e "$3" ] || return 1; printf 'LINK:%s\n' "$2" > "$3"; }
sync() { return 0; }
df() { echo 'Filesystem 1K-blocks Used Available Use% Mounted'; echo "fixture 100000 0 $(bb cat '__FIXTURE__/free') 0% $2"; }
mount() {
    echo "$*" >> '__FIXTURE__/mount-calls'
    case "$2" in
    remount,rw*)
      [ ! -e '__FIXTURE__/fail-rw' ] || return 1
      bb sed -i 's/ext4 ro,relatime/ext4 rw,relatime/' '__FIXTURE__/proc/mounts';;
    remount,ro*)
      [ ! -e '__FIXTURE__/fail-ro' ] || return 1
      bb sed -i 's/ext4 rw,relatime/ext4 ro,relatime/' '__FIXTURE__/proc/mounts';;
    *) return 1;; esac
}
'''.replace('__WRAPPERS__',wrappers).replace('__HOST__',HOST.as_posix()).replace('__FIXTURE__',prefix)
    rewritten=rewritten.replace('export PATH','export PATH\n'+mocks,1)
    # BusyBox-Windows rejects symlink creation, so only the virtual boundary above is used.
    script=f/'package/scripts/opds-system-model.sh'
    script.write_text(rewritten,encoding='utf-8',newline='\n')
    return f,script

def run(f,script,action,code):
    result=subprocess.run([str(HOST),'sh',str(script),action],capture_output=True,text=True,timeout=30)
    (f/f'{action}-{len(results)}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    require(result.returncode==code,f'{f.name} {action}: expected {code}, got {result.returncode}\n{result.stdout}{result.stderr}')
    results.append({'fixture':f.name,'action':action,'exit':result.returncode})
    return result

def unchanged(f):
    require((f/'ebrmain/lib/libopds_app_lib.so').read_text()=='LINK:../cramfs/lib/libopds_app_lib.so\n','Original link changed')
    require((f/'ebrmain/cramfs/lib/libopds_app_lib.so').read_bytes()==original.read_bytes(),'Compressed original changed')

