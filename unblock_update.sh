#!/bin/sh

ensure_set() {
	ipset create "$1" hash:net -exist >/dev/null 2>&1
}

flush_set() {
	ensure_set "$1"
	ipset flush "$1" >/dev/null 2>&1
}

[ -x /opt/etc/ndm/fs.d/100-ipset.sh ] && /opt/etc/ndm/fs.d/100-ipset.sh start

flush_set unblocktor
flush_set unblocksh
flush_set unblockvmess
flush_set unblockvless
flush_set unblockvless2
flush_set unblocktroj
flush_set unblockvpn

if ls -d /opt/etc/unblock/vpn-*.txt >/dev/null 2>&1; then
for vpn_file_names in /opt/etc/unblock/vpn-*; do
vpn_file_name=$(echo "$vpn_file_names" | awk -F '/' '{print $5}' | sed 's/.txt//')
# shellcheck disable=SC2116
unblockvpn=$(echo unblock"$vpn_file_name")
flush_set "$unblockvpn"
done
fi

[ -x /opt/etc/ndm/netfilter.d/100-redirect.sh ] && table=nat /opt/etc/ndm/netfilter.d/100-redirect.sh
[ -x /opt/etc/ndm/netfilter.d/100-redirect.sh ] && table=mangle /opt/etc/ndm/netfilter.d/100-redirect.sh

/opt/bin/unblock_dnsmasq.sh
/opt/etc/init.d/S56dnsmasq restart
/opt/bin/unblock_ipset.sh &