#!/bin/sh
set -eu
cd -- "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 2; }
root=$PWD
for folder in .cache .cache/tmp .tools .tools/downloads .tools/python-runtime; do
    [ ! -L "$folder" ] || fail "Refusing redirected project directory: $folder"
    mkdir -p "$folder"
    resolved=$(CDPATH= cd -- "$folder" && pwd -P)
    case "$resolved/" in "$root/"*) :;; *) fail "Directory escapes project: $folder";; esac
done
export TMPDIR="$PWD/.cache/tmp" TMP="$PWD/.cache/tmp" TEMP="$PWD/.cache/tmp"
export PYTHONDONTWRITEBYTECODE=1 PIP_CACHE_DIR="$PWD/.cache/pip" PIP_CONFIG_FILE=/dev/null
case "${1:-}" in test) shift; set -- --test "$@";; esac
no_download=0
for argument do
    case "$argument" in --check|--offline) no_download=1;; esac
done
test_python() {
    "$1" -I -B -c 'import sys,ssl,hashlib,zipfile; sys.exit(0 if sys.version_info >= (3,11) else 2)' >/dev/null 2>&1
}
stage=
cleanup() {
    if [ -n "$stage" ] && [ -d "$stage" ]; then
        case "$stage" in "$root"/.tools/python-runtime/.install.*) rm -rf -- "$stage";; *) return 1;; esac
    fi
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
if [ -n "${PYTHON:-}" ]; then
    python_bin=$PYTHON
    test_python "$python_bin" || fail "Explicit PYTHON override cannot run Python 3.11+ with SSL: $PYTHON. Unset PYTHON for automatic local bootstrap."
else
    . "$root/scripts/python-bootstrap.lock"
    [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || fail 'Automatic bootstrap supports Linux x86-64 (Debian/Ubuntu).'
    runtime=$root/.tools/python-runtime/$LINUX_INSTALL
    [ ! -L "$runtime" ] || fail 'Refusing a redirected Python runtime'
    python_bin=$runtime/$LINUX_EXE
    if [ ! -d "$runtime" ]; then
        [ "$no_download" = 0 ] || fail "Local Python $VERSION is missing; check/offline mode never downloads. Run sh build.sh to prepare everything automatically."
        archive=$root/.tools/downloads/$LINUX_ARCHIVE
        [ ! -L "$archive" ] && [ ! -L "$archive.part" ] || fail 'Refusing redirected Python download files'
        if [ ! -f "$archive" ]; then
            printf '[DOWNLOAD] Portable Python %s -> .tools/downloads/\n' "$VERSION"
            if command -v curl >/dev/null 2>&1; then
                curl -q --fail --location --retry 2 --connect-timeout 20 --max-time 300 --proto '=https' --proto-redir '=https' --output "$archive.part" "$LINUX_URL" || fail 'Python download failed; check network/proxy/certificates.'
            elif command -v wget >/dev/null 2>&1; then
                wget --no-config --no-hsts --timeout=120 --tries=3 -O "$archive.part" "$LINUX_URL" || fail 'Python download failed; GNU wget with --no-hsts support is required (or curl).'
            else
                fail 'A TLS download client (curl or GNU wget) is required; Python itself need not be installed.'
            fi
            [ "$(sha256sum "$archive.part" | awk '{print $1}')" = "$LINUX_SHA256" ] || fail 'Python download SHA-256 mismatch; nothing was extracted.'
            mv -- "$archive.part" "$archive"
        fi
        [ "$(sha256sum "$archive" | awk '{print $1}')" = "$LINUX_SHA256" ] || fail "Python archive SHA-256 mismatch: $archive"
        stage=$(mktemp -d "$root/.tools/python-runtime/.install.XXXXXX")
        printf '[SETUP] Extracting verified Python inside .tools/python-runtime/\n'
        tar -tzf "$archive" > "$stage/member-list"
        awk '/^\// || /(^|\/)\.\.($|\/)/ {bad=1} END {exit bad}' "$stage/member-list" || fail 'Unsafe Python archive path'
        tar -xzf "$archive" -C "$stage" --no-same-owner --no-same-permissions
        test_python "$stage/$LINUX_EXE" || fail 'Extracted Python failed its SSL/version check; not activated.'
        [ "$("$stage/$LINUX_EXE" -I -B -c 'import sys; print(sys.version.split()[0])')" = "$VERSION" ] || fail 'Wrong Python bootstrap version'
        rm -- "$stage/member-list"
        [ ! -e "$runtime" ] || fail 'Python destination appeared while bootstrapping'
        mv -- "$stage" "$runtime"
        stage=
    fi
    test_python "$python_bin" || fail "Local Python is damaged: $runtime. Inspect this cache before retrying."
    [ "$("$python_bin" -I -B -c 'import sys; print(sys.version.split()[0])')" = "$VERSION" ] || fail 'Wrong cached Python bootstrap version'
    printf '[OK] Local Python: %s\n' "$python_bin"
fi
if [ -z "${SSL_CERT_FILE:-}" ] && [ -r /etc/ssl/certs/ca-certificates.crt ]; then
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
fi
exec "$python_bin" -I -B scripts/build.py "$@"
