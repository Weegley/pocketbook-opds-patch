#!/bin/sh
# Called under the physical.guard lock by the manager or an early boot hook.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODE=${1:-manual}
. "$HERE/physical-common.sh"
check_system read-only
[ ! -L "$STATE" ] && [ "$(metadata "$STATE")" = '0:0:drwx------' ] || die 'Unexpected recovery state'
if [ "$MODE" = boot ]; then
    require_early_boot
    if [ -e "$FIRST_HOOK" ]; then check_hook "$FIRST_HOOK" first;
    elif [ -e "$ROLLBACK_HOOK" ]; then check_hook "$ROLLBACK_HOOK" rollback;
    else die 'No recognized physical recovery hook'; fi
    # The old installer uses an empty mkdir lock. A reboot can leave it behind.
    if [ -d "$STATE/lock" ] && [ ! -L "$STATE/lock" ]; then
        rmdir "$STATE/lock" || die 'Nonempty recovery lock; refusing to delete it'
    fi
elif [ "$MODE" != manual ]; then
    die 'Invalid recovery mode'
fi
if original_link_present; then
    echo 'RECOVERY_ORIGINAL: system already points to the original SquashFS library.'
    exit 0
fi
if [ "$MODE" != boot ]; then
    case "$(get_phase)" in installing|await-first-boot|await-confirmation|committed) :;; *) die 'No recorded physical installation to restore';; esac
fi
check_system
prepare_state
# This managed installer accepted only the observed stock link owner 1000:1000.
# Recovery uses the separately verified, untouched SquashFS original, even if a
# power failure damaged the pending file or a p9 backup receipt.
owner=1000:1000
if [ ! -f "$STATE/original.so" ] || [ "$(hash "$STATE/original.so")" != "$ORIGINAL" ]; then
    echo 'BACKUP_WARNING: p9 backup is unavailable/damaged; using the SHA-verified SquashFS original.'
fi
[ ! -d "$TARGET" ] || die 'Library path became a directory'
echo 'RECOVERY: restoring the recorded original link, including a missing/damaged pending library.'
begin_write
candidate=/ebrmain/lib/.libopds_app_lib.so.recovery.$$
[ ! -e "$candidate" ] && [ ! -L "$candidate" ] || die 'Recovery temporary name occupied'
ln -s "$LINK" "$candidate"
TEMP=$candidate
chown -h "$owner" "$TEMP"
mv -f "$TEMP" "$TARGET"
TEMP=
check_original_link
finish_write
echo 'RECOVERY_RESTORED: original link and mount options restored.'
