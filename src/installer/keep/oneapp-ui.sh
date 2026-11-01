#!/bin/sh
# One public application; root is used only to stage a protected boot job.
set -u
PATH=/sbin:/bin:/usr/sbin:/usr/bin
export PATH
unset LD_PRELOAD LD_LIBRARY_PATH ENV BASH_ENV
umask 077
. "$(dirname -- "$0")/i18n.sh"
case "${OPDS_UI_LANGUAGE:-}" in ru|en) :;; *) opds_select_language;; esac
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
CACHE=${HERE%/scripts}
USERDIR=/mnt/ext1/system/.opds-authors-611-open-rooted
PENDING=$USERDIR/pending
ROOT_HELPER=/mnt/secure/su
ORIGINAL=e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98
PATCHED=c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5
SU_HASH=7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb
hash() { sha256sum "$1" | awk '{print $1}'; }
notice() { dialog 1 OPDS "$1" OK >/dev/null 2>&1 || :; }
ask() { dialog 2 OPDS "$1" "$2" "$(opds_text cancel)" >/dev/null 2>&1; [ "$?" = 1 ]; }
finish() {
    code=$?
    trap - EXIT HUP INT TERM
    sync
    # Only this invocation's mktemp directory is removable, never USERDIR/state.
    case "$CACHE" in "$USERDIR"/run.*) rm -rf "$CACHE";; esac
    exit "$code"
}
trap finish EXIT
trap 'exit 130' HUP INT TERM
exec 8> "$USERDIR/ui.guard"
flock -n 8 || { notice "$(opds_text busy)"; exit 1; }
[ "$(cat /ebrmain/.version)" = ver=6.11.2001 ] &&
grep -qx model=Pocket632 /ebrmain/config/device.cfg &&
grep -qx variant=U632 /ebrmain/config/device.cfg || { notice "$(opds_text wrong_firmware)"; exit 1; }
[ "$(hash /ebrmain/cramfs/lib/libopds_app_lib.so)" = "$ORIGINAL" ] || { notice "$(opds_text original_mismatch)"; exit 1; }
current=$(hash /ebrmain/lib/libopds_app_lib.so)
case "$current" in "$ORIGINAL"|"$PATCHED") :;; *) notice "$(opds_text unknown_library)"; exit 1;; esac
. "$HERE/prepare-library.sh"
prepare_library "$CACHE/payload" "$CACHE" || { notice "$(opds_text prepare_failed)"; exit 1; }
action=
if [ -f "$PENDING" ] && [ ! -L "$PENDING" ]; then
    action=$(cat "$PENDING")
    case "$action" in install|uninstall) :;; *) notice "$(opds_text bad_state)"; exit 1;; esac
    # Root remains installed; protected boot state decides whether a job can resume.

else
    if [ "$current" = "$ORIGINAL" ]; then
        action=install
        ask "$(opds_text install_keep_root)" "$(opds_text install)" || exit 0
    else
        action=uninstall
        ask "$(opds_text uninstall_keep_root)" "$(opds_text uninstall)" || exit 0
    fi
    rm -f "$USERDIR/rolled-back"
    printf '%s\n' "$action" > "$PENDING.new" && mv -f "$PENDING.new" "$PENDING" || exit 1
    sync
fi
LOG=/mnt/ext1/OPDS_Rooted_611_${action}.log
[ ! -L "$LOG" ] || { notice "$(opds_text log_symlink)"; exit 1; }
exec >> "$LOG" 2>&1
echo '=== New invocation: Rooted patch open v9 UI ==='
echo "ACTION=$action"
date
id
echo "CURRENT_SHA256=$current"
if [ ! -x "$ROOT_HELPER" ]; then
    echo 'RESULT=ROOT_REQUIRED; this variant never installs root.'
    notice "$(opds_text root_required)"
    exit 1
fi

if [ -L "$ROOT_HELPER" ] || [ "$(hash "$ROOT_HELPER")" != "$SU_HASH" ]; then
    echo 'RESULT=REFUSED: root helper differs from the embedded v8 helper.'
    notice "$(opds_text foreign_helper_keep)"
    exit 1
fi
# FD8 belongs only to this UI. Do not let root descendants retain its lock.
"$ROOT_HELPER" /bin/sh "$HERE/oneapp-root.sh" stage "$action" 8>&-
code=$?
echo "STAGE_EXIT=$code"
if [ "$code" != 0 ]; then
    echo 'RESULT=STAGE_FAILED; root was not removed; inspect the log.'
    notice "$(opds_text stage_failed)"
    exit "$code"
fi
echo 'RESULT=QUEUED; boot will perform the operation and retain existing root.'
sync
notice "$(opds_text queued_keep)"
sync
iv2sh reboot
echo 'REBOOT_REQUEST_RETURNED: if no reboot occurs, reboot normally; do not launch old Install/Keep/Restore apps.'
exit 0
