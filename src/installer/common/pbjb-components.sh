#!/bin/sh
# MIT. Read user-obtained upstream components; never fetch latest on the reader.
opds_get_pbjb() {
    destination=$1
    if [ -d "$destination/pbjb" ] && [ ! -L "$destination/pbjb" ]; then
        component_dir=$destination/pbjb
    else
        component_dir=/mnt/ext1/system/opds-pbjb/8f1fb889d575237f2b292e88df6aabf552142d87
    fi
    [ ! -L "$component_dir" ] || return 1
    for component in jailbreak su; do
        case "$component" in
            jailbreak) expected=a523b9e77519fa0dd657268c4ad59d3ea1bcb4e07355687e6e372b68ff8c6a10;;
            su) expected=7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb;;
        esac
        [ -f "$component_dir/$component" ] && [ ! -L "$component_dir/$component" ] &&
        [ "$(sha256sum "$component_dir/$component" | awk '{print $1}')" = "$expected" ] || return 1
    done
    if [ "$component_dir" != "$destination/pbjb" ]; then
        [ ! -e "$destination/pbjb" ] && [ ! -L "$destination/pbjb" ] || return 1
        mkdir "$destination/pbjb" || return 1
        for component in jailbreak su; do
            cp "$component_dir/$component" "$destination/pbjb/$component" || return 1
        done
    fi
    # The UI checks the copies again after copying to /var/tmp for execution.
    return 0
}
