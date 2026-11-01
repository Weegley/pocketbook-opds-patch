#!/bin/sh
# Shared helpers for guarded physical installation and boot recovery.
set -- --functions-only
. "$HERE/opds-system.sh"
FIRST_HOOK=/mnt/secure/runonce/00-opds-physical-a.sh
ROLLBACK_HOOK=/mnt/secure/runonce/00-opds-physical-b.sh
RUNTIME=$STATE/physical-runtime/scripts
PHASE_FILE=$STATE/physical-phase

physical_state() {
    if [ ! -e "$STATE" ] && [ ! -L "$STATE" ]; then mkdir -m 700 "$STATE"; fi
    [ ! -L "$STATE" ] && [ "$(metadata "$STATE")" = '0:0:drwx------' ] || die 'Unexpected state directory'
    [ ! -L "$STATE/physical.guard" ] || die 'Unexpected guard symlink'
    exec 9> "$STATE/physical.guard"
    flock -n 9 || die 'Another physical operation is running'
}
get_phase() {
    if [ -f "$PHASE_FILE" ] && [ ! -L "$PHASE_FILE" ]; then cat "$PHASE_FILE"; else printf '%s\n' none; fi
}
set_phase() {
    TEMP=$(mktemp "$STATE/physical-phase.XXXXXX")
    printf '%s\n' "$1" > "$TEMP"
    chmod 600 "$TEMP"
    mv -f "$TEMP" "$PHASE_FILE"
    TEMP=
    sync
}
hook_command() {
    printf '/mnt/secure/su /bin/sh %s/physical-boot.sh %s\n' "$RUNTIME" "$1"
}
check_hook() {
    [ ! -L "$1" ] && [ -f "$1" ] && [ "$(metadata "$1")" = '0:0:-rwxr-xr-x' ] || die "Unexpected hook: $1"
    grep -qxF "$(hook_command "$2")" "$1" || die "Unrecognized hook: $1"
}
remove_hook() {
    if [ -e "$1" ] || [ -L "$1" ]; then check_hook "$1" "$2"; rm -f "$1"; fi
}
remove_physical_hooks() {
    remove_hook "$FIRST_HOOK" first
    remove_hook "$ROLLBACK_HOOK" rollback
    sync
}
write_hook() {
    [ ! -e "$1" ] && [ ! -L "$1" ] || die "Hook already exists: $1"
    TEMP=$(mktemp "$1.new.XXXXXX")
    printf '%s\n' '#!/bin/sh' "$(hook_command "$2")" 'exit $?' > "$TEMP"
    chown 0:0 "$TEMP"
    chmod 755 "$TEMP"
    mv -f "$TEMP" "$1"
    TEMP=
    sync
}
check_physical_root_helper() {
    [ ! -L /mnt/secure/su ] && [ "$(metadata /mnt/secure/su)" = '0:0:-rwsr-xr-x' ] || die 'Persistent root helper is required'
    result=$(su - sreader -c '/mnt/secure/su /bin/id -u') || die 'Root helper failed under sreader'
    [ "$result" = 0 ] || die 'Root helper did not obtain UID 0'
}
stage_physical_runtime() {
    mkdir -p "$RUNTIME"
    chmod 700 "$STATE/physical-runtime" "$RUNTIME"
    for script in opds-system.sh physical-common.sh physical-boot.sh physical-recover.sh; do
        cp "$HERE/$script" "$RUNTIME/$script"
        chmod 700 "$RUNTIME/$script"
    done
}
original_link_present() {
    [ -L "$TARGET" ] && [ "$(readlink "$TARGET")" = "$LINK" ] && [ "$(hash "$TARGET")" = "$ORIGINAL" ]
}
require_early_boot() {
    for procdir in "$PROC"/[0-9]*; do
        executable=$(readlink -f "$procdir/exe" 2>/dev/null) || continue
        case "$executable" in */explorer-3) die 'Recovery hook ran after Explorer; no automatic write attempted';; esac
    done
}
