#!/bin/sh
# PocketBook 632 U632.6.11.2001 only. No privilege escalation or process restart.
set -eu
PATH=/sbin:/bin:/usr/sbin:/usr/bin
export PATH
umask 077
BASE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TARGET=/ebrmain/lib/libopds_app_lib.so
CANONICAL=/ebrmain/cramfs/lib/libopds_app_lib.so
STATE=/mnt/secure/opds-authors-6.11
PAYLOAD=$BASE/payload/libopds_app_lib.so
ORIGINAL=e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98
PATCHED=c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5
LINK=../cramfs/lib/libopds_app_lib.so
MOUNTS=/proc/mounts
PROC=/proc
RW=0
ORIGINAL_OPTIONS=
LOCKED=0
TEMP=

die() { echo "ERROR: $*" >&2; exit 1; }
hash() { sha256sum "$1" | awk '{print $1}'; }
metadata() { ls -ldn "$1" | awk '{print $3 ":" $4 ":" $1}'; }
inode_of() { ls -Lid "$1" | awk '{print $1}'; }
expect_hash() { [ "$(hash "$1")" = "$2" ] || die "SHA-256 mismatch: $1"; }
mount_options() { awk '$2=="/ebrmain" {print $4}' "$MOUNTS"; }
is_ro() { case ,$(mount_options), in *,ro,*) return 0;; *) return 1;; esac; }
cleanup() {
    code=$?
    trap - EXIT HUP INT TERM
    set +e
    if [ -n "$TEMP" ] && ! rm -f "$TEMP"; then
        echo "ERROR: could not remove temporary file: $TEMP" >&2
        code=1
    fi
    if [ "$RW" = 1 ]; then
        if ! sync || ! mount -o "remount,$ORIGINAL_OPTIONS" /ebrmain || ! is_ro || [ "$(mount_options)" != "$ORIGINAL_OPTIONS" ]; then
            echo 'ERROR: could not restore /ebrmain to read-only; inspect mounts before proceeding.' >&2
            code=1
        fi
    fi
    if [ "$LOCKED" = 1 ]; then rmdir "$STATE/lock" || code=1; fi
    exit "$code"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

check_identity() {
    [ "$(id -u)" = 0 ] || die 'Run from an existing root shell. This script does not obtain root.'
    [ "$(cat /ebrmain/.version)" = 'ver=6.11.2001' ] || die 'Wrong firmware version'
    grep -qx 'model=Pocket632' /ebrmain/config/device.cfg || die 'Wrong device model'
    grep -qx 'variant=U632' /ebrmain/config/device.cfg || die 'Wrong firmware variant'
}

check_device_mount() {
    mountpoint=$1
    expected_node=$2
    expected_numbers=$3
    # /dev is a symlink to /var/dev on the real reader. Resolve both sides.
    expected_device=$(readlink -f "$expected_node") || die "Cannot resolve $expected_node"
    [ -n "$expected_device" ] || die "Empty device path: $expected_node"
    mounted_source=$(awk -v point="$mountpoint" '$2==point {print $1}' "$MOUNTS")
    resolved_source=$(readlink -f "$mounted_source") || die "Cannot resolve mount source for $mountpoint"
    [ "$resolved_source" = "$expected_device" ] || die "Unexpected backing device for $mountpoint"
    awk -v point="$mountpoint" -v numbers="$expected_numbers" '$5==point {n++; if ($3!=numbers || $4!="/") bad=1} END {exit (n!=1 || bad)}' "$PROC/self/mountinfo" || die "Unexpected device numbers or mount root for $mountpoint"
}

check_system() {
    check_identity
    [ "$(readlink /usr/lib)" = /ebrmain/lib ] || die 'Unexpected /usr/lib layout'
    [ ! -L /ebrmain/lib ] && [ -d /ebrmain/lib ] || die 'Unexpected library directory'
    [ "$(metadata /ebrmain/lib)" = '0:0:drwxr-xr-x' ] || die 'Unsafe library directory permissions'
    [ "$(readlink -f /dev/ebrmain)" = "$(readlink -f /dev/mmcblk0p8)" ] || die 'Unexpected system block device'
    [ "$(readlink -f /dev/secure)" = "$(readlink -f /dev/mmcblk0p9)" ] || die 'Unexpected backup block device'
    check_device_mount /ebrmain /dev/mmcblk0p8 179:8
    check_device_mount /mnt/secure /dev/mmcblk0p9 179:9
    if [ "${1:-write}" = write ]; then
        [ "$(cat /sys/class/block/mmcblk0/ro)" = 0 ] || die 'MMC device is read-only'
        [ "$(cat /sys/class/block/mmcblk0p8/ro)" = 0 ] || die 'System partition is read-only'
    fi
    [ "$(awk '$2=="/ebrmain" {n++} END {print n+0}' "$MOUNTS")" = 1 ] || die 'Ambiguous /ebrmain mount'
    ORIGINAL_OPTIONS=$(mount_options)
    if [ "${1:-write}" = write ]; then
        case ,$ORIGINAL_OPTIONS, in *,noexec,*) die '/ebrmain is noexec; the replacement library could not be mapped executable';; esac
    fi
    fs=$(awk '$2=="/ebrmain" {print $3}' "$MOUNTS")
    case "$fs" in ext2|ext3|ext4) :;; *) die 'Unsupported /ebrmain filesystem';; esac
    [ "$(awk '$2=="/ebrmain/cramfs" {print $3}' "$MOUNTS")" = squashfs ] || die 'Unexpected compressed filesystem'
    # Reject file/directory overlays that could hide the real installation path.
    awk '$2=="/ebrmain/lib" || $2=="/usr/lib" || $2=="/ebrmain/lib/libopds_app_lib.so" || $2=="/ebrmain/cramfs/lib" || $2=="/ebrmain/cramfs/lib/libopds_app_lib.so" {bad=1} END {exit bad}' "$MOUNTS" || die 'A bind/overlay is active; remove it first'
    expect_hash "$CANONICAL" "$ORIGINAL"
    [ "$(metadata "$CANONICAL")" = '0:0:-rw-r--r--' ] || die 'Unexpected original ELF permissions'
}

check_original_link() {
    [ -L "$TARGET" ] || die 'Expected the original symlink'
    [ "$(readlink "$TARGET")" = "$LINK" ] || die 'Unexpected symlink target'
    [ "$(readlink -f "$TARGET")" = "$CANONICAL" ] || die 'Unexpected resolved library path'
    expect_hash "$TARGET" "$ORIGINAL"
}

prepare_state() {
    if [ ! -e "$STATE" ] && [ ! -L "$STATE" ]; then mkdir -m 700 "$STATE"; fi
    [ ! -L "$STATE" ] && [ -d "$STATE" ] || die 'Unsafe backup directory'
    [ "$(metadata "$STATE")" = '0:0:drwx------' ] || die 'Unsafe backup directory permissions'
    mkdir "$STATE/lock" || die 'Another operation or stale lock exists; inspect before removing the empty lock'
    LOCKED=1
}

check_backup() {
    [ ! -L "$STATE/original.so" ] && [ -f "$STATE/original.so" ] || die 'Original backup is missing or unsafe'
    expect_hash "$STATE/original.so" "$ORIGINAL"
    [ "$(cat "$STATE/original-link.txt")" = "$LINK" ] || die 'Backup link receipt mismatch'
    owner=$(cat "$STATE/original-link-owner.txt")
    case "$owner" in ''|*[!0-9:]*|:*|*:) die 'Invalid saved link owner';; esac
    [ "$(printf '%s' "$owner" | tr -cd : | wc -c)" = 1 ] || die 'Invalid saved link owner'
}

begin_write() {
    is_ro || die 'Expected an initially read-only /ebrmain; inspect the current mount first'
    RW=1 # Even a failed mount may have changed flags; cleanup attempts read-only restoration.
    write_options=$(printf '%s\n' "$ORIGINAL_OPTIONS" | awk -F, '{for(i=1;i<=NF;i++) printf "%s%s",i==1?"":",",$i=="ro"?"rw":$i}')
    mount -o "remount,$write_options" /ebrmain || die 'Remount failed; no library replacement attempted'
    case ,$(mount_options), in *,rw,*) :;; *) die 'Remount did not enable writes';; esac
}

finish_write() {
    sync || die 'Sync failed; backup retained'
    mount -o "remount,$ORIGINAL_OPTIONS" /ebrmain || die 'Read-only remount failed; backup retained'
    is_ro || die '/ebrmain is not read-only'
    [ "$(mount_options)" = "$ORIGINAL_OPTIONS" ] || die 'Original mount flags were not restored'
    RW=0
}

verify_inode_loaded() {
    loaded_source=$1
    source_mountpoint=$2
    expected_hash=${3:-$PATCHED}
    expect_hash "$loaded_source" "$expected_hash"
    inode=$(inode_of "$loaded_source")
    devhex=$(awk -v point="$source_mountpoint" '$5==point {split($3,d,":"); printf "%02x:%02x",d[1],d[2]}' "$PROC/self/mountinfo")
    [ -n "$devhex" ] || die 'Cannot determine mount device'
    found=0
    pending=0
    for procdir in "$PROC"/[0-9]*; do
        executable=$(readlink -f "$procdir/exe" 2>/dev/null) || continue
        case "$executable" in */explorer-3) :;; *) continue;; esac
        found=1
        echo "explorer pid=${procdir##*/}; expected backing device=$devhex inode=$inode"
        [ "$(readlink "$procdir/ns/mnt")" = "$(readlink "$PROC/self/ns/mnt")" ] || die 'Explorer is in another mount namespace'
        awk '/libopds_app_lib[.]so|bind-payload[.]so/ {print}' "$procdir/maps"
        if ! awk -v ino="$inode" -v dev="$devhex" '/libopds_app_lib[.]so|bind-payload[.]so/ {seen=1; if ($5 != ino || $4 != dev) bad=1} END {exit (!seen || bad)}' "$procdir/maps"; then
            pending=1
        fi
    done
    [ "$found" = 1 ] || die 'Explorer process not found; loading cannot be confirmed'
    [ "$pending" = 0 ] || { echo 'PENDING_RESTART: Explorer still maps another inode; integration is not confirmed.'; return 3; }
    echo 'VERIFIED: Explorer maps the inode whose SHA-256 matches the expected library.'
}

verify_loaded() {
    [ ! -L "$TARGET" ] || die 'Physical installation is not present'
    verify_inode_loaded "$TARGET" /ebrmain
}

if [ "${1:-}" = --functions-only ]; then return 0; fi
action=${1:-check}
case "$action" in install|uninstall|check|verify) :;; *) die 'Usage: opds-system.sh install|uninstall|check|verify';; esac
check_system
case "$action" in
check)
    echo "version=U632.6.11.2001; model=PB632; filesystem=$fs; options=$(mount_options)"
    ls -ln "$TARGET" "$CANONICAL"
    sha256sum "$TARGET" "$CANONICAL"
    df -Pk /ebrmain /mnt/secure
    ;;
verify) verify_loaded;;
install)
    [ ! -e /mnt/secure/runonce/00-opds-authors-once.sh ] && [ ! -L /mnt/secure/runonce/00-opds-authors-once.sh ] || die 'Disarm the pending bind trial first'
    expect_hash "$PAYLOAD" "$PATCHED"
    prepare_state
    if [ ! -L "$TARGET" ] && [ -f "$TARGET" ] && [ "$(hash "$TARGET")" = "$PATCHED" ]; then
        [ "$(metadata "$TARGET")" = '0:0:-rw-r--r--' ] || die 'Installed patch has unexpected permissions'
        check_backup
        echo 'Already installed; use verify after a normal reboot.'
        exit 0
    fi
    check_original_link
    is_ro || die 'Expected read-only /ebrmain'
    free_kb=$(df -Pk /ebrmain | awk 'END {print $4}')
    case "$free_kb" in ''|*[!0-9]*) die 'Cannot determine free system space';; esac
    [ "$free_kb" -ge 2645 ] || die 'Need at least 2645 KiB available on /ebrmain; no resizing or deletion will be attempted'
    if [ ! -e "$STATE/original.so" ] && [ ! -L "$STATE/original.so" ]; then
        secure_kb=$(df -Pk /mnt/secure | awk 'END {print $4}')
        [ "$secure_kb" -ge 2048 ] || die 'Need at least 2048 KiB available for backup'
        TEMP=$(mktemp "$STATE/original.new.XXXXXX")
        cat "$CANONICAL" > "$TEMP"
        expect_hash "$TEMP" "$ORIGINAL"
        chmod 600 "$TEMP"
        mv -f "$TEMP" "$STATE/original.so"
        TEMP=
        printf '%s\n' "$LINK" > "$STATE/original-link.txt"
        ls -ldn "$TARGET" | awk '{print $3 ":" $4}' > "$STATE/original-link-owner.txt"
        sync
    fi
    check_backup
    begin_write
    TEMP=$(mktemp /ebrmain/lib/.libopds_app_lib.so.new.XXXXXX)
    cat "$PAYLOAD" > "$TEMP"
    chown 0:0 "$TEMP"
    chmod 644 "$TEMP"
    expect_hash "$TEMP" "$PATCHED"
    sync
    # Rename over the symlink itself. Never open the existing destination for writing.
    mv -f "$TEMP" "$TARGET"
    TEMP=
    expect_hash "$TARGET" "$PATCHED"
    finish_write
    echo 'INSTALLED: original SquashFS unchanged; backup in /mnt/secure/opds-authors-6.11.'
    echo 'No process was restarted. Reboot normally, then run: sh scripts/opds-system.sh verify'
    ;;
uninstall)
    prepare_state
    check_backup
    if [ -L "$TARGET" ]; then
        check_original_link
        echo 'Already restored; backup retained.'
        exit 0
    fi
    [ -f "$TARGET" ] || die 'System library is neither an expected file nor link'
    expect_hash "$TARGET" "$PATCHED"
    begin_write
    candidate=/ebrmain/lib/.libopds_app_lib.so.restore.$$
    [ ! -e "$candidate" ] && [ ! -L "$candidate" ] || die 'Recovery temporary name is already occupied'
    ln -s "$LINK" "$candidate"
    TEMP=$candidate
    chown -h "$owner" "$TEMP"
    mv -f "$TEMP" "$TARGET"
    TEMP=
    check_original_link
    finish_write
    echo 'RESTORED: original symlink and link owner restored; external backup retained. Reboot normally.'
    ;;
esac
