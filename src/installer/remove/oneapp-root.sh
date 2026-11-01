#!/bin/sh
# Protected early-boot transaction for the already device-tested SO, not firmware.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODE=${1:-}
REQUEST=${2:-}
CONSENT=${3:-}
. "$HERE/physical-common.sh"
JOB=$STATE/oneapp-runtime
HOOK=/mnt/secure/runonce/00-opds-oneapp-611.sh
PHASE=$STATE/oneapp-phase
ACTION_FILE=$STATE/oneapp-action
ROOT_HELPER=/mnt/secure/su
SU_HASH=7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb
BOOT_LOG=
ROOT_POLICY=remove
POLICY_FILE=$STATE/oneapp-root-policy
check_identity

check_job_policy() {
    saved_policy=remove
    if [ -f "$POLICY_FILE" ] && [ ! -L "$POLICY_FILE" ]; then saved_policy=$(cat "$POLICY_FILE"); fi
    [ "$saved_policy" = "$ROOT_POLICY" ] || die 'Pending job belongs to another root policy; resume with the same app variant'
}
phase() { if [ -f "$PHASE" ] && [ ! -L "$PHASE" ]; then cat "$PHASE"; else echo none; fi; }
save_phase() {
    TEMP=$(mktemp "$STATE/oneapp-phase.XXXXXX")
    printf '%s\n' "$1" > "$TEMP"
    chmod 600 "$TEMP"
    mv -f "$TEMP" "$PHASE"
    TEMP=
    sync
}
check_su() {
    [ ! -L "$ROOT_HELPER" ] && [ "$(metadata "$ROOT_HELPER")" = '0:0:-rwsr-xr-x' ] || die 'Unexpected root-helper owner/mode/type'
    expect_hash "$ROOT_HELPER" "$SU_HASH"
}
hook_text() {
    printf '%s\n' '#!/bin/sh' '[ -x /mnt/secure/su ] || exit 0' "/mnt/secure/su /bin/sh $JOB/scripts/oneapp-root.sh boot" 'exit $?'
}
check_our_hook() {
    [ ! -L "$HOOK" ] && [ "$(metadata "$HOOK")" = '0:0:-rwxr-xr-x' ] || die 'Unexpected boot hook'
    [ "$(cat "$HOOK")" = "$(hook_text)" ] || die 'Foreign boot hook content'
}
no_other_hooks() {
    [ ! -L /mnt/secure/runonce ] || die 'Unsafe runonce symlink'
    for other in /mnt/secure/runonce/*.sh; do
        [ -e "$other" ] || [ -L "$other" ] || continue
        [ "$other" = "$HOOK" ] || die "Another runonce hook exists: $other. Finish/cancel the old trial or services operation first."
    done
}
check_result() {
    check_system read-only
    is_ro || die '/ebrmain is not read-only'
    if [ "$1" = install ]; then
        [ ! -L "$TARGET" ] && [ "$(metadata "$TARGET")" = '0:0:-rw-r--r--' ] || die 'Unexpected patched file metadata'
        expect_hash "$TARGET" "$PATCHED"
        check_backup
    else
        check_original_link
        [ "$(metadata "$TARGET")" = '1000:1000:lrwxrwxrwx' ] || die 'Original symlink owner changed'
    fi
    echo "DISK_VERIFIED: action=$1; /ebrmain=ro; live Explorer mapping is not asserted."
}
public_log_available() {
    # Never create logs under an unmounted /mnt/ext1 or follow Linux symlinks as root.
    awk '$5=="/mnt/ext1" && $3=="179:1" && $4=="/" {ok=1} END {exit !ok}' "$PROC/self/mountinfo" &&
    awk '$2=="/mnt/ext1" && $3=="vfat" && $4 ~ /(^|,)rw(,|$)/ {ok=1} END {exit !ok}' "$MOUNTS"
}
export_boot_log() {
    [ -n "$BOOT_LOG" ] || return 0
    if public_log_available; then
        cat "$BOOT_LOG" >> "/mnt/ext1/OPDS_Non_rooted_611_${REQUEST}.log" || return 1
        sync
    else
        echo 'PUBLIC_LOG_DEFERRED: root-owned boot log retained in /mnt/secure/opds-authors-6.11.'
    fi
}
boot_exit() {
    code=$?
    trap - EXIT HUP INT TERM
    set +e
    echo "BOOT_EXIT=$code"
    [ "$code" = 0 ] || echo 'RESULT=BOOT_FAILED; root may remain for recovery; do not assume completion.'
    export_boot_log || :
    sync
    exit "$code"
}
cleanup_root() {
    check_result "$1"
    no_other_hooks
    check_su
    check_our_hook
    printf '%s\n' "$1" > "$STATE/oneapp-disk-action"
    sync
    save_phase cleanup-pending
    # From here no recovery script requires su. Current process is already UID 0.
    # A power loss between hook removal and su removal is resumed by the same app.
    rm -f "$HOOK"
    sync
    /bin/chattr -i "$ROOT_HELPER" || die 'Cannot clear immutable bit; root retained'
    /bin/rm -f "$ROOT_HELPER" || die 'Cannot remove root helper'
    [ ! -e "$ROOT_HELPER" ] && [ ! -L "$ROOT_HELPER" ] || die 'Root helper still exists'
    sync
    save_phase complete
    echo "RESULT=COMPLETE action=$REQUEST; disk_action=$1; ROOT_HELPER_REMOVED=1"
    echo 'No root access or root-dependent OPDS boot hook is retained.'
    if [ "$REQUEST" = "$1" ] && public_log_available; then
        # A later launch may immediately offer the reverse action, like pbjb.
        rm -f /mnt/ext1/system/.opds-authors-611-open/pending
        sync
    fi
}

case "$MODE" in
bootstrap)
    # Called by the unmodified upstream `jailbreak [cmd]`, already with UID 0.
    # Stage before the reboot instead of patching the helper's UI or its ELF.
    case "$REQUEST" in install|uninstall) :;; *) die 'Invalid bootstrap action';; esac
    check_system read-only
    is_ro || die 'Bootstrap requires read-only /ebrmain'
    [ ! -e "$ROOT_HELPER" ] && [ ! -L "$ROOT_HELPER" ] || die 'Root helper already exists; use stage instead'
    if /bin/sh "$HERE/oneapp-root.sh" bootstrap-stage "$REQUEST"; then
        echo 'BOOTSTRAP_QUEUED: persistent root exists only until the next early boot transaction.'
        sync
        /sbin/reboot
    else
        code=$?
        echo "BOOTSTRAP_STAGE_FAILED=$code; no system-library write was requested."
        # Do not strand a newly installed root helper after a rejected preflight.
        if [ -e "$HOOK" ] || [ -L "$HOOK" ]; then
            check_our_hook
            echo 'BOOTSTRAP_HOOK_EXISTS: retaining root for the queued job/recovery.'
            sync
            /sbin/reboot
            exit "$code"
        fi
        if [ -e "$ROOT_HELPER" ] || [ -L "$ROOT_HELPER" ]; then
            [ ! -L "$ROOT_HELPER" ] || die 'Unexpected helper symlink during bootstrap cleanup'
            expect_hash "$ROOT_HELPER" "$SU_HASH"
            /bin/chattr -i "$ROOT_HELPER" || echo 'ROOT_CLEANUP_WARNING: chattr failed; attempting normal unlink.'
            /bin/rm -f "$ROOT_HELPER"
        fi
        sync
        echo 'BOOTSTRAP_ROOT_REMOVED: reboot clears the exploit page-cache change.'
        /sbin/reboot
        exit "$code"
    fi
    ;;
bootstrap-stage)
    case "$REQUEST" in install|uninstall) :;; *) die 'Invalid bootstrap action';; esac
    check_system read-only
    is_ro || die 'Bootstrap requires read-only /ebrmain'
    [ ! -e "$ROOT_HELPER" ] && [ ! -L "$ROOT_HELPER" ] || die 'Root helper already exists'
    expect_hash "$BASE/pbjb/su" "$SU_HASH"
    no_other_hooks
    /bin/chmod 755 /mnt/secure
    /bin/cp "$BASE/pbjb/su" "$ROOT_HELPER"
    /bin/chown 0:0 "$ROOT_HELPER"
    /bin/chmod 4755 "$ROOT_HELPER"
    /bin/chattr +i "$ROOT_HELPER"
    sync
    /bin/sh "$HERE/oneapp-root.sh" stage "$REQUEST" temporary-root-confirmed
    ;;
stage)
    case "$CONSENT" in remove-existing-root-confirmed|temporary-root-confirmed) :;; *) die 'Explicit root-removal consent is required';; esac
    case "$REQUEST" in install|uninstall) :;; *) die 'Expected install or uninstall';; esac
    check_system read-only
    is_ro || die 'Reboot first: /ebrmain must be read-only'
    physical_state
    check_su
    check_physical_root_helper
    no_other_hooks
    if [ -e "$HOOK" ] || [ -L "$HOOK" ]; then
        check_our_hook
        check_job_policy
        [ "$(cat "$ACTION_FILE")" = "$REQUEST" ] || die 'Another action is already queued'
        echo 'ONEAPP_QUEUED: existing protected job retained; reboot normally.'
        exit 0
    fi
    case "$(get_phase)" in none|restored|rolled-back|committed) :;; *) die 'An older physical trial is pending; finish or restore it first';; esac
    case "$(phase)" in
        none|complete) :;;
        queued)
            check_job_policy
            [ "$(cat "$ACTION_FILE")" = "$REQUEST" ] || die 'Queued action mismatch'
            [ ! -L "$JOB" ] && [ "$(metadata "$JOB")" = '0:0:drwx------' ] || die 'Unsafe queued runtime'
            (cd "$JOB" && sha256sum -c SHA256SUMS) || die 'Queued runtime is damaged'
            TEMP=$(mktemp "$HOOK.new.XXXXXX")
            hook_text > "$TEMP"; chmod 755 "$TEMP"; chown 0:0 "$TEMP"
            mv -f "$TEMP" "$HOOK"; TEMP=; sync
            echo 'ONEAPP_QUEUED: interrupted hook creation completed.'
            exit 0;;
        cleanup-pending)
            check_job_policy
            disk_action=$(cat "$STATE/oneapp-disk-action")
            case "$disk_action" in install|uninstall) :;; *) die 'Invalid cleanup result';; esac
            check_result "$disk_action"
            if [ "$(cat "$ACTION_FILE")" = "$REQUEST" ]; then
                # Re-arm cleanup only; the library will not be modified again.
                TEMP=$(mktemp "$HOOK.new.XXXXXX")
                hook_text > "$TEMP"; chmod 755 "$TEMP"; chown 0:0 "$TEMP"
                mv -f "$TEMP" "$HOOK"; TEMP=; sync
                echo 'ONEAPP_QUEUED: unfinished root removal will resume at boot.'
                exit 0
            fi
            # A power loss after su removal can leave this receipt unfinished.
            # A new, explicitly requested reverse operation may supersede it.
            save_phase complete
            echo 'PREVIOUS_DISK_RESULT_VERIFIED: staging the requested reverse operation.'
            ;;
        *) die 'Interrupted job without its hook; inspect oneapp-phase before proceeding';;
    esac
    if [ -L "$TARGET" ]; then
        check_original_link
        [ "$(metadata "$TARGET")" = '1000:1000:lrwxrwxrwx' ] || die 'Unexpected stock link owner'
    else
        expect_hash "$TARGET" "$PATCHED"
        [ "$(metadata "$TARGET")" = '0:0:-rw-r--r--' ] || die 'Unexpected installed patch metadata'
        check_backup
    fi
    [ ! -e /mnt/secure/runonce ] || [ "$(metadata /mnt/secure/runonce)" = '0:0:drwxr-xr-x' ] ||
        [ "$(metadata /mnt/secure/runonce)" = '102:102:drwxr-xr-x' ] ||
        [ "$(metadata /mnt/secure/runonce)" = '102:102:drwxrwx---' ] || die 'Unexpected runonce permissions'
    if [ ! -d /mnt/secure/runonce ]; then mkdir -m 755 /mnt/secure/runonce; fi
    # A private root-owned copy is required: no boot code/payload is loaded from FAT.
    STAGING=$(mktemp -d "$STATE/oneapp-stage.XXXXXX")
    mkdir "$STAGING/scripts" "$STAGING/payload"
    for script in opds-system.sh physical-common.sh physical-recover.sh oneapp-root.sh; do
        [ ! -L "$HERE/$script" ] || die 'Source script is a symlink'
        cp "$HERE/$script" "$STAGING/scripts/$script"
        chmod 700 "$STAGING/scripts/$script"
    done
    expect_hash "$PAYLOAD" "$PATCHED"
    cat "$PAYLOAD" > "$STAGING/payload/libopds_app_lib.so"
    chmod 600 "$STAGING/payload/libopds_app_lib.so"
    chmod 700 "$STAGING" "$STAGING/scripts" "$STAGING/payload"
    (cd "$STAGING" && sha256sum scripts/*.sh payload/libopds_app_lib.so > SHA256SUMS)
    if [ -e "$JOB" ] || [ -L "$JOB" ]; then
        [ ! -L "$JOB" ] && [ "$(metadata "$JOB")" = '0:0:drwx------' ] || die 'Unsafe old runtime'
        # Retain it for diagnostics instead of recursively deleting privileged paths.
        old=$(mktemp -d "$STATE/oneapp-previous.XXXXXX")
        mv "$JOB" "$old/runtime"
    fi
    mv "$STAGING" "$JOB"
    printf '%s\n' "$REQUEST" > "$ACTION_FILE"
    chmod 600 "$ACTION_FILE"
    printf '%s\n' "$ROOT_POLICY" > "$POLICY_FILE"
    chmod 600 "$POLICY_FILE"
    save_phase queued
    TEMP=$(mktemp "$HOOK.new.XXXXXX")
    hook_text > "$TEMP"; chown 0:0 "$TEMP"; chmod 755 "$TEMP"
    mv -f "$TEMP" "$HOOK"; TEMP=
    sync
    echo 'ONEAPP_QUEUED: protected boot job staged; no live system library was changed.'
    ;;
apply)
    # A separate ash process preserves set -e even when boot inspects its status.
    case "$REQUEST" in install|uninstall) :;; *) die 'Invalid apply action';; esac
    check_system
    require_early_boot
    if [ "$REQUEST" = install ]; then
        set_phase installing
        /bin/sh "$HERE/opds-system.sh" install
        check_result install
        set_phase committed
    else
        /bin/sh "$HERE/opds-system.sh" uninstall
        check_result uninstall
        set_phase restored
    fi
    ;;
boot)
    physical_state
    [ ! -L "$ACTION_FILE" ] || die 'Unsafe action receipt'
    REQUEST=$(cat "$ACTION_FILE")
    case "$REQUEST" in install|uninstall) :;; *) die 'Invalid saved action';; esac
    BOOT_LOG=$(mktemp "$STATE/oneapp-${REQUEST}-boot.log.XXXXXX")
    trap boot_exit EXIT
    exec >> "$BOOT_LOG" 2>&1
    echo "=== New invocation: Non-rooted patch open v9 boot; action=$REQUEST phase=$(phase) ==="
    date
    check_system read-only
    require_early_boot
    check_our_hook
    check_job_policy
    check_su
    no_other_hooks
    [ "$HERE" = "$JOB/scripts" ] || die 'Boot runtime is outside the protected directory'
    [ ! -L "$JOB" ] && [ "$(metadata "$JOB")" = '0:0:drwx------' ] || die 'Unsafe protected runtime'
    (cd "$JOB" && sha256sum -c SHA256SUMS) || die 'Protected runtime is damaged'
    if [ -d "$STATE/lock" ] && [ ! -L "$STATE/lock" ]; then rmdir "$STATE/lock" || die 'Nonempty legacy lock'; fi
    case "$(phase)" in
        queued)
            save_phase writing
            if /bin/sh "$HERE/oneapp-root.sh" apply "$REQUEST"; then
                cleanup_root "$REQUEST"
            else
                echo 'APPLY_FAILED: restoring verified original before allowing GUI startup.'
                set_phase installing
                /bin/sh "$HERE/physical-recover.sh" manual
                set_phase restored
                echo 'OPERATION_ROLLED_BACK: requested patch was not applied; original restored.'
                if public_log_available; then printf '%s\n' "$REQUEST" > /mnt/ext1/system/.opds-authors-611-open/rolled-back; sync; fi
                cleanup_root uninstall
            fi
            ;;
        writing)
            echo 'INTERRUPTED_WRITE: restoring original instead of guessing whether the write completed.'
            set_phase installing
            /bin/sh "$HERE/physical-recover.sh" manual
            set_phase restored
            echo 'OPERATION_ROLLED_BACK: interrupted transaction restored to original.'
            if public_log_available; then printf '%s\n' "$REQUEST" > /mnt/ext1/system/.opds-authors-611-open/rolled-back; sync; fi
            cleanup_root uninstall
            ;;
        cleanup-pending)
            check_job_policy
            disk_action=$(cat "$STATE/oneapp-disk-action")
            case "$disk_action" in install|uninstall) :;; *) die 'Invalid cleanup result';; esac
            cleanup_root "$disk_action";;
        *) die 'Unexpected boot transaction phase';;
    esac
    ;;
*) die 'Usage: oneapp-root.sh stage install|uninstall (internal boot/apply only)';;
esac
