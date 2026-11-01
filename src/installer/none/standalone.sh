#!/bin/sh
# Same tested host and SO, packaged as one file; no root or system modification.
set -u
. "$(dirname -- "$0")/i18n.sh"
case "${OPDS_UI_LANGUAGE:-}" in ru|en) :;; *) opds_select_language;; esac
HERE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
check_hash() { [ "$(sha256sum "$1" | awk '{print $1}')" = "$2" ]; }
fail() { dialog 3 OPDS "$(opds_text standalone_unsupported)" OK >/dev/null 2>&1 || :; exit 1; }
check_hash /ebrmain/bin/opds.app 73a187e0dbf5c33be71bba6f33fd796e059460302389d216b8d932a2b581b417 || fail
case "$(sha256sum /ebrmain/lib/libopds_app_lib.so | awk '{print $1}')" in
    e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98|c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5) :;;
    *) fail;;
esac
check_hash "$HERE/libpb_opds_host.so" @HOST_SHA@ || fail
. "$(dirname -- "$0")/prepare-library.sh"
prepare_library "$HERE/lib" "$HERE" || fail
check_hash "$HERE/lib/libopds_app_lib.so" c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5 || fail
PB_OPDS_SAVED_PRELOAD=${LD_PRELOAD-}
PB_OPDS_SAVED_LIBRARY_PATH=${LD_LIBRARY_PATH-}
LD_LIBRARY_PATH="$HERE/lib:/ebrmain/lib:/lib:/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
LD_PRELOAD="$HERE/libpb_opds_host.so${LD_PRELOAD:+:$LD_PRELOAD}"
export PB_OPDS_SAVED_PRELOAD PB_OPDS_SAVED_LIBRARY_PATH LD_LIBRARY_PATH LD_PRELOAD
# Keep the original, working exec launch path and PID. No new callback/bridge code.
exec /ebrmain/bin/opds.app >/dev/null 2>&1
