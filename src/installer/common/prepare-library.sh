#!/bin/sh
# MIT. No writes to SquashFS or /ebrmain/lib. Safe to run as the normal reader.
prepare_library() (
    set -eu
    directory=$1
    package=$2
    source=/ebrmain/cramfs/lib/libopds_app_lib.so
    expected=e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98
    result=c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5
    log=/mnt/ext1/OPDS_prepare_611.log
    [ ! -L "$log" ] || exit 1
    exec >> "$log" 2>&1 || exit 1
    echo '=== On-device library preparation: open v9 ==='
    date
    [ "$(cat /ebrmain/.version)" = ver=6.11.2001 ] &&
    grep -qx model=Pocket632 /ebrmain/config/device.cfg &&
    grep -qx variant=U632 /ebrmain/config/device.cfg || { echo 'PREPARE_REFUSED: model/firmware'; exit 1; }
    [ ! -L "$source" ] && [ -f "$source" ] &&
    [ "$(wc -c < "$source" | tr -d ' ')" = 598364 ] &&
    [ "$(sha256sum "$source" | awk '{print $1}')" = "$expected" ] || { echo 'PREPARE_REFUSED: original size/SHA/type'; exit 1; }
    [ ! -L "$directory" ] || exit 1
    mkdir -p "$directory" || exit 1
    [ ! -L "$directory/.prepare.guard" ] || exit 1
    exec 6> "$directory/.prepare.guard" || exit 1
    flock -n 6 || { echo 'PREPARE_BUSY'; exit 1; }
    output=$directory/libopds_app_lib.so
    if [ -e "$output" ] || [ -L "$output" ]; then
        [ ! -L "$output" ] && [ -f "$output" ] &&
        [ "$(wc -c < "$output" | tr -d ' ')" = 610748 ] &&
        [ "$(sha256sum "$output" | awk '{print $1}')" = "$result" ] || { echo 'PREPARE_REFUSED: damaged cache; close OPDS before removing its cache'; exit 1; }
        echo 'PREPARE_CACHED: exact universal-v8 library verified'
        exit 0
    fi
    tempdir=$(mktemp -d "$directory/.patch.XXXXXX") || exit 1
    trap 'code=$?; rm -f "$tempdir/libopds_app_lib.so"; rmdir "$tempdir" || :; exit "$code"' EXIT
    trap 'exit 130' HUP INT TERM
    "$package/tools/opds-patcher" Pocket632 U632.6.11.2001 "$source" "$tempdir/libopds_app_lib.so" || exit 1
    [ "$(sha256sum "$tempdir/libopds_app_lib.so" | awk '{print $1}')" = "$result" ] || exit 1
    chmod 600 "$tempdir/libopds_app_lib.so" || exit 1
    sync || exit 1
    # Serialized, same-filesystem rename. The live system symlink is untouched.
    [ ! -e "$output" ] && [ ! -L "$output" ] || exit 1
    mv "$tempdir/libopds_app_lib.so" "$output" || exit 1
    sync || exit 1
    echo "PREPARE_COMPLETE: SHA256=$result"
)
