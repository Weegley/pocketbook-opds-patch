"""Execute physical-install state transitions in Windows ash with virtual Linux boundaries."""
import json
from pathlib import Path
import re
import runpy
import shlex
import subprocess

import model_core
from model_support import ROOT as B, sub_hashes
baseline=vars(model_core)
fixture=baseline['fixture']; require=baseline['require']; HOST=baseline['HOST']
ORIGINAL=baseline['original'].read_bytes(); PATCHED=baseline['payload'].read_bytes()
results=[]
names=['physical-common.sh','physical-recover.sh']

def make(name):
    f,model=fixture('physical-'+name)
    (f/'device-dir').write_text('var/dev\n')
    (f/'free').write_text('8752\n')
    (f/'mnt/secure/su').write_bytes(b'Fixture only')
    (f/'mnt/secure/runonce').mkdir()
    # Keep the OS mocks, including virtual symlinks; all installer control flow stays real.
    code=model.read_text()
    code=code.replace('*/00-opds-authors-once.sh)', '*/00-opds-authors-once.sh|*/00-opds-physical-a.sh|*/00-opds-physical-b.sh)')
    code=code.replace('metadata() { case', 'metadata() { if is_link "$1"; then echo 1000:1000:lrwxrwxrwx; return; fi; case')
    code=code.replace('s/ext4 ro,relatime/ext4 rw,relatime/','s/ext2 ro,relatime/ext2 rw,relatime/')
    code=code.replace('s/ext4 rw,relatime/ext4 ro,relatime/','s/ext2 rw,relatime/ext2 ro,relatime/')
    code=code.replace('export PATH','export PATH\nflock() { [ ! -e "'+f.as_posix()+'/fail-flock" ]; }',1)
    core=model.with_name('opds-system.sh');core.write_text(code,encoding='utf-8',newline='\n')
    for name in names:
        text=sub_hashes((B/'src/installer/common'/name).read_text(encoding='utf-8'))
        paths=['/mnt/secure','/ebrmain','/proc']
        text=re.sub('|'.join(re.escape(p) for p in paths),lambda m:f.as_posix()+m[0],text)
        text=re.sub(r'\[\s+(!\s+)?-L\s+([^\]]+?)\s*\]',lambda m:('! ' if m[1] else '')+'is_link '+m[2],text)
        text=re.sub(r'(?m)^(\s*)(if )?/bin/sh ',lambda m:m[1]+(m[2] or '')+"'"+HOST.as_posix()+"' sh ",text)
        core.with_name(name).write_text(text,encoding='utf-8',newline='\n')
    for name in ['proc/mounts','proc/self/mountinfo']:
        path=f/name
        path.write_text(path.read_text().replace('ext4','ext2').replace('ro,relatime','ro,relatime,errors=remount-ro'))
    with (f/'proc/self/mountinfo').open('a') as stream:
        stream.write(f'3 1 7:0 / {f.as_posix()}/ebrmain/cramfs ro - squashfs /dev/loop0 ro\n')
    return f,core.with_name('physical-manage.sh')

def call(f,script,arg,expected):
    p=subprocess.run([str(HOST),'sh',str(script),arg],capture_output=True,text=True,timeout=30)
    (f/f'physical-{len(results)}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
    require(p.returncode==expected,f'{f.name} {arg}: expected {expected}, got {p.returncode}\n{p.stdout}{p.stderr}')
    results.append({'case':f.name,'action':arg,'exit':p.returncode})
    return p

def phase(f):return (f/'mnt/secure/opds-authors-6.11/physical-phase').read_text().strip()
def target(f):return f/'ebrmain/lib/libopds_app_lib.so'
def stock(f):
    require(target(f).read_bytes()==b'LINK:../cramfs/lib/libopds_app_lib.so\n','Factory link not restored')
    require((f/'ebrmain/cramfs/lib/libopds_app_lib.so').read_bytes()==ORIGINAL,'SquashFS original changed')
    require('ext2 ro,relatime,errors=remount-ro' in (f/'proc/mounts').read_text(),'Mount flags not restored')
def gui(f):
    (f/'proc/123').mkdir(exist_ok=True)
    device='07:00' if target(f).read_bytes().startswith(b'LINK:') else 'b3:08'
    (f/'proc/123/maps').write_text(f'93000-94000 r-xp 00093000 {device} 777 /ebrmain/lib/libopds_app_lib.so\n')
def boot(f,expected=0):
    # The independent ash glob test below confirms this snapshot is the native for-loop behavior.
    proc=f/'proc/123'
    if proc.exists():(proc/'maps').unlink();proc.rmdir()
    hooks=sorted((f/'mnt/secure/runonce').glob('*.sh'))
    for hook in hooks:
        if not hook.exists():continue
        command=shlex.split(hook.read_text().splitlines()[1])
        require(command[1]=='/bin/sh','Unexpected hook command')
        call(f,Path(command[2]),command[3],expected)
        if expected==0 and hook.exists():hook.unlink() # native monitor removes a successful runonce script
    gui(f)

