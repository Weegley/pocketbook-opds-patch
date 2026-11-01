from model_core import *
for script in (B/'src/installer/common').iterdir():
    if script.suffix in ['.sh','.app']:
        parsed=subprocess.run([str(HOST),'sh','-n',str(script)],capture_output=True,text=True)
        require(parsed.returncode==0,f'Shell syntax: {script.name}: {parsed.stderr}')
        results.append({'syntax':script.name,'exit':0})

f,s=fixture('roundtrip')
run(f,s,'check',0);unchanged(f)
run(f,s,'install',0)
require((f/'ebrmain/lib/libopds_app_lib.so').read_bytes()==payload.read_bytes(),'Wrong installed bytes')
require((f/'mnt/secure/opds-authors-6.11/original.so').read_bytes()==original.read_bytes(),'Backup differs')
run(f,s,'install',0)
run(f,s,'verify',0)
(f/'proc/123/maps').write_text('93000-94000 r-xp 00093000 b3:08 888 /ebrmain/lib/libopds_app_lib.so\n')
run(f,s,'verify',3)
run(f,s,'uninstall',0);unchanged(f)
run(f,s,'uninstall',0);unchanged(f)

f,s=fixture('reader-var-dev-layout')
(f/'device-dir').write_text('var/dev\n')
(f/'free').write_text('8752\n')
for filename in ['proc/mounts','proc/self/mountinfo']:
    p=f/filename
    p.write_text(p.read_text().replace('ext4','ext2').replace('ro,relatime','ro,relatime,errors=remount-ro'))
run(f,s,'check',0);unchanged(f)

f,s=fixture('wrong-mounted-device')
p=f/'proc/self/mountinfo';p.write_text(p.read_text().replace('179:8','179:9'))
run(f,s,'install',1);unchanged(f)

f,s=fixture('wrong-mount-root')
p=f/'proc/self/mountinfo';p.write_text(p.read_text().replace('179:8 / ','179:8 /unexpected-subdirectory '))
run(f,s,'install',1);unchanged(f)

for name in ['nonroot','version','model','original-hash','payload-hash','space','read-only-device','active-bind','fail-rw','fail-copy','fail-copy-cleanup','unrecognized-target']:
    f,s=fixture(name)
    if name=='nonroot':(f/'uid').write_text('102\n')
    elif name=='version':(f/'ebrmain/.version').write_text('ver=6.5.1383\n')
    elif name=='model':(f/'ebrmain/config/device.cfg').write_text('model=Pocket633\nvariant=U632\n')
    elif name=='original-hash':(f/'ebrmain/cramfs/lib/libopds_app_lib.so').write_bytes(b'wrong')
    elif name=='payload-hash':(f/'package/payload/libopds_app_lib.so').write_bytes(b'wrong')
    elif name=='space':(f/'free').write_text('101\n')
    elif name=='read-only-device':(f/'sys/class/block/mmcblk0/ro').write_text('1\n')
    elif name=='active-bind':
        with (f/'proc/mounts').open('a') as stream:stream.write(f'/dev/secure {f.as_posix()}/ebrmain/cramfs/lib/libopds_app_lib.so ext4 rw 0 0\n')
    elif name=='unrecognized-target':(f/'ebrmain/lib/libopds_app_lib.so').write_bytes(b'foreign')
    elif name=='fail-copy-cleanup':(f/'fail-copy').touch();(f/'fail-rm').touch()
    else:(f/name).touch()
    run(f,s,'install',1)
    if name not in ['original-hash','unrecognized-target']:unchanged(f)
    if name in ['fail-rw','fail-copy','fail-copy-cleanup']:
        require('ext4 ro,relatime' in (f/'proc/mounts').read_text(),'Did not restore read-only mode')

f,s=fixture('failed-ro-after-commit');(f/'fail-ro').touch()
r=run(f,s,'install',1)
require((f/'ebrmain/lib/libopds_app_lib.so').read_bytes()==payload.read_bytes(),'Unexpected post-commit state')
require('could not restore' in r.stderr,'Missing critical mount diagnostic')

