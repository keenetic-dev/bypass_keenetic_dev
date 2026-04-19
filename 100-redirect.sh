#!/bin/sh

# 2023. Keenetic DNS bot /  Проект: bypass_keenetic / Автор: tas_unn
# GitHub: https://github.com/tas-unn/bypass_keenetic
# Данный бот предназначен для управления обхода блокировок на роутерах Keenetic
# Демо-бот: https://t.me/keenetic_dns_bot
#
# Файл: 100-redirect.sh, Версия 2.1.9, последнее изменение: 03.05.2023, 21:10
# Доработал: NetworK (https://github.com/znetworkx)

#!/bin/sh

# shellcheck disable=SC2154
[ "$type" = "ip6tables" ] && exit 0
[ "$table" != "mangle" ] && [ "$table" != "nat" ] && exit 0

ip4t() {
	if ! iptables -C "$@" &>/dev/null; then
		 iptables -A "$@" || exit 0
	fi
}

local_ip=$(ip -4 addr show br0 | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -n1)

if [ -z "$local_ip" ]; then
    echo "[100-redirect.sh] br0 has no IPv4 address, skip DNS redirect" >&2
    exit 0
fi

for protocol in udp tcp; do
	if [ -z "$(iptables-save 2>/dev/null | grep "$protocol --dport 53 -j DNAT")" ]; then
	iptables -I PREROUTING -w -t nat -p "$protocol" --dport 53 -j DNAT --to "$local_ip"; fi
done


#if [ -z "$(iptables-save 2>/dev/null | grep "--dport 53 -j DNAT")" ]; then
#    iptables -w -t nat -I PREROUTING -p udp --dport 53 -j DNAT --to 192.168.1.1
#    iptables -w -t nat -I PREROUTING -p tcp --dport 53 -j DNAT --to 192.168.1.1
#fi

# перенаправление 53 порта для br0 на определенный IP
#if [ -z "$(iptables-save 2>/dev/null | grep "udp --dport 53 -j DNAT")" ]; then
#    iptables -w -t nat -I PREROUTING -i br0 -p udp --dport 53 -j DNAT --to 192.168.1.1
#    iptables -w -t nat -I PREROUTING -i br0 -p tcp --dport 53 -j DNAT --to 192.168.1.1
#fi

# перенаправление 53 порта для sstp на определенный IP
#if [ -z "$(iptables-save 2>/dev/null | grep "tcp --dport 53 -j DNAT")" ]; then
#    iptables -w -t nat -I PREROUTING -i sstp0 -p tcp --dport 53 -j DNAT --to 192.168.1.1
#    iptables -w -t nat -I PREROUTING -i sstp0 -p udp --dport 53 -j DNAT --to 192.168.1.1
#fi


if [ -z "$(iptables-save 2>/dev/null | grep unblocksh)" ]; then
	ipset create unblocksh hash:net -exist 2>/dev/null

	# достаточно таких правил, для работы на всех интерфейсах (br0, br1, sstp0, sstp2, etc)
	iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082
	iptables -I PREROUTING -w -t nat -p udp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082

	# если у вас другой конфиг dnsmasq, и вы слушаете только определенный ip, раскоментируйте следующие строки, поставьте свой ip
	#iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblocksh dst --dport 53 -j DNAT --to 192.168.1.1
	#iptables -I PREROUTING -w -t nat -p udp -m set --match-set unblocksh dst --dport 53 -j DNAT --to 192.168.1.1

	# если вы хотите что бы обход работал только для определнных интерфейсов, закоментируйте строки выше, и раскоментируйте эти (br0)
	#iptables -I PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082
	#iptables -I PREROUTING -w -t nat -i br0 -p udp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082
	#iptables -I PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblocksh dst --dport 53 -j DNAT --to 192.168.1.1
	#iptables -I PREROUTING -w -t nat -i br0 -p udp -m set --match-set unblocksh dst --dport 53 -j DNAT --to 192.168.1.1

	# если вы хотите что бы обход работал только для определённых интерфейсов, закоментируйте строки выше, и раскоментируйте эти (sstp0)
	#iptables -I PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082
	#iptables -I PREROUTING -w -t nat -i sstp0 -p udp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082
	#iptables -I PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblocksh dst --dport 53 -j DNAT --to 192.168.1.1
	#iptables -I PREROUTING -w -t nat -i sstp0 -p udp -m set --match-set unblocksh dst --dport 53 -j DNAT --to 192.168.1.1

	# если вы хотите, что бы у вас были проблемы с entware (stmb, rest api), раскоментируйте эту строку
	#iptables -A OUTPUT -t nat -p tcp -m set --match-set unblocksh dst -j REDIRECT --to-port 1082
fi


if [ -z "$(iptables-save 2>/dev/null | grep unblocktor)" ]; then
  ipset create unblocktor hash:net -exist 2>/dev/null
	iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
	iptables -I PREROUTING -w -t nat -p udp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
	#iptables -I PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
	#iptables -I PREROUTING -w -t nat -i br0 -p udp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
	#iptables -A PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141

	#iptables -I PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
	#iptables -I PREROUTING -w -t nat -i sstp0 -p udp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
	#iptables -A PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblocktor dst -j REDIRECT --to-port 9141
fi


if [ -z "$(iptables-save 2>/dev/null | grep unblockvmess)" ]; then
  ipset create unblockvmess hash:net -exist 2>/dev/null
	iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810
	iptables -I PREROUTING -w -t nat -p udp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810

	#iptables -I PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810
	#iptables -I PREROUTING -w -t nat -i br0 -p udp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810
	#iptables -A PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810 #в целом не имеет смысла

	#iptables -I PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810
	#iptables -I PREROUTING -w -t nat -i sstp0 -p udp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810
	#iptables -A PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblockvmess dst -j REDIRECT --to-port 10810 #в целом не имеет смысла
fi


ipset create unblockvless hash:net -exist 2>/dev/null
while iptables -t nat -C PREROUTING -w -p tcp -m set --match-set unblockvless dst -j REDIRECT --to-port 10811 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p tcp -m set --match-set unblockvless dst -j REDIRECT --to-port 10811
done
while iptables -t nat -C PREROUTING -w -p tcp -m set --match-set unblockvless dst -j REDIRECT --to-port 10812 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p tcp -m set --match-set unblockvless dst -j REDIRECT --to-port 10812
done
if ! iptables -t nat -C PREROUTING -w -p tcp -m set --match-set unblockvless dst -j REDIRECT --to-port 10812 2>/dev/null; then
	iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblockvless dst -j REDIRECT --to-port 10812
fi
while iptables -t nat -C PREROUTING -w -p udp -m set --match-set unblockvless dst -j REDIRECT --to-port 10811 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p udp -m set --match-set unblockvless dst -j REDIRECT --to-port 10811
done
while iptables -t nat -C PREROUTING -w -p udp -m set --match-set unblockvless dst -j REDIRECT --to-port 10812 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p udp -m set --match-set unblockvless dst -j REDIRECT --to-port 10812
done
if ! iptables -C FORWARD -w -p udp -m set --match-set unblockvless dst --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null; then
	iptables -I FORWARD -w -p udp -m set --match-set unblockvless dst --dport 443 -j REJECT --reject-with icmp-port-unreachable
fi


ipset create unblockvless2 hash:net -exist 2>/dev/null
while iptables -t nat -C PREROUTING -w -p tcp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10813 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p tcp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10813
done
while iptables -t nat -C PREROUTING -w -p tcp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p tcp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814
done
while iptables -t nat -C PREROUTING -w -p udp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10813 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p udp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10813
done
while iptables -t nat -C PREROUTING -w -p udp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814 2>/dev/null; do
	iptables -t nat -D PREROUTING -w -p udp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814
done
while iptables -C FORWARD -w -p udp -m set --match-set unblockvless2 dst --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null; do
	iptables -D FORWARD -w -p udp -m set --match-set unblockvless2 dst --dport 443 -j REJECT --reject-with icmp-port-unreachable
done

vless2_key_path=""
for candidate in /opt/etc/xray/vless2.key /opt/etc/v2ray/vless2.key; do
	if [ -s "$candidate" ]; then
		vless2_key_path="$candidate"
		break
	fi
done

if [ -n "$vless2_key_path" ]; then
	if ! iptables -t nat -C PREROUTING -w -p tcp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814 2>/dev/null; then
		iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814
	fi
	if ! iptables -t nat -C PREROUTING -w -p udp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814 2>/dev/null; then
		iptables -I PREROUTING -w -t nat -p udp -m set --match-set unblockvless2 dst -j REDIRECT --to-port 10814
	fi
	if ! iptables -C FORWARD -w -p udp -m set --match-set unblockvless2 dst --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null; then
		iptables -I FORWARD -w -p udp -m set --match-set unblockvless2 dst --dport 443 -j REJECT --reject-with icmp-port-unreachable
	fi
fi


if [ -z "$(iptables-save 2>/dev/null | grep unblocktroj)" ]; then
  ipset create unblocktroj hash:net -exist 2>/dev/null
	iptables -I PREROUTING -w -t nat -p tcp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829
	iptables -I PREROUTING -w -t nat -p udp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829

	#iptables -I PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829
	#iptables -I PREROUTING -w -t nat -i br0 -p udp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829
	#iptables -A PREROUTING -w -t nat -i br0 -p tcp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829 #в целом не имеет смысла

	#iptables -I PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829
	#iptables -I PREROUTING -w -t nat -i sstp0 -p udp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829
	#iptables -A PREROUTING -w -t nat -i sstp0 -p tcp -m set --match-set unblocktroj dst -j REDIRECT --to-port 10829 #в целом не имеет смысла
fi


TAG="100-redirect.sh"

get_default_vpn_interface() {
local config_path="/opt/etc/bot_config.py"
if [ -f "/opt/etc/bot/bot_config.py" ]; then
config_path="/opt/etc/bot/bot_config.py"
fi

check_allow_vpn_in_config=$(grep "vpn_allowed" "$config_path" 2>/dev/null | head -1 | sed 's/=/ /g' | tr -d '"' | awk '{print $2}')
if [ -z "${check_allow_vpn_in_config}" ]; then
    vpn_services="IKE|SSTP|OpenVPN|Wireguard|L2TP"
else
    vpn_services=$(echo "$check_allow_vpn_in_config")
fi

curl -s localhost:79/rci/show/interface | grep -E "$vpn_services" | grep id | awk '{print $2}' | tr -d '",' | uniq -u | while read -r vpn; do
    [ -z "$vpn" ] && continue
    vpn_link_up=$(curl -s localhost:79/rci/show/interface/"$vpn"/link | tr -d '"')
    if [ "$vpn_link_up" = "up" ]; then
        printf '%s\n' "$vpn"
        break
    fi
done
}

add_vpn_mark_rules() {
unblockvpn="$1"
vpn_type="$2"

[ -z "$unblockvpn" ] && return 0
[ -z "$vpn_type" ] && return 0

vpn_type_lower=$(echo "$vpn_type" | tr [:upper:] [:lower:])
get_vpn_fwmark_id=$(grep "$vpn_type_lower" /opt/etc/iproute2/rt_tables | awk '{print $1}')

if [ -z "${get_vpn_fwmark_id}" ]; then
    return 0
fi

vpn_mark_id=$(echo 0xd"$get_vpn_fwmark_id")

if iptables-save 2>/dev/null | grep -q "$unblockvpn"; then
    vpn_rule_ok=$(echo Правила для "$unblockvpn" уже есть.)
    echo "$vpn_rule_ok"
    return 0
fi

info_vpn_rule=$(echo ipset: "$unblockvpn", mark_id: "$vpn_mark_id")
logger -t "$TAG" "$info_vpn_rule"

ipset create "$unblockvpn" hash:net -exist 2>/dev/null

fastnat=$(curl -s localhost:79/rci/show/version | grep ppe)
software=$(curl -s localhost:79/rci/show/rc/ppe | grep software -C1  | head -1 | awk '{print $2}' | tr -d ",")
hardware=$(curl -s localhost:79/rci/show/rc/ppe | grep hardware -C1  | head -1 | awk '{print $2}' | tr -d ",")
if [ -z "$fastnat" ] && [ "$software" = "false" ] && [ "$hardware" = "false" ]; then
    info=$(echo "VPN: fastnat, swnat и hwnat ВЫКЛЮЧЕНЫ, правила добавлены")
    logger -t "$TAG" "$info"
    iptables -A PREROUTING -w -t mangle -p tcp -m set --match-set "$unblockvpn" dst -j MARK --set-mark "$vpn_mark_id"
    iptables -A PREROUTING -w -t mangle -p udp -m set --match-set "$unblockvpn" dst -j MARK --set-mark "$vpn_mark_id"
else
    info=$(echo "VPN: fastnat, swnat и hwnat ВКЛЮЧЕНЫ, правила добавлены")
    logger -t "$TAG" "$info"
    iptables -A PREROUTING -w -t mangle -m conntrack --ctstate NEW -m set --match-set "$unblockvpn" dst -j CONNMARK --set-mark "$vpn_mark_id"
    iptables -A PREROUTING -w -t mangle -j CONNMARK --restore-mark
fi
}

default_vpn_interface=$(get_default_vpn_interface)
if [ -f /opt/etc/unblock/vpn.txt ]; then
add_vpn_mark_rules unblockvpn "$default_vpn_interface"
fi

if ls -d /opt/etc/unblock/vpn-*.txt >/dev/null 2>&1; then
for vpn_file_name in /opt/etc/unblock/vpn*; do
# выполняется цикл поиска файлов для vpn
vpn_unblock_name=$(echo $vpn_file_name | awk -F '/' '{print $5}' | sed 's/.txt//');
unblockvpn=$(echo unblock"$vpn_unblock_name");

# проверяем есть ли подключенный линк к vpn
#vpn_type=$(echo "$unblockvpn" | awk -F '-' '{print $3}') # old version
vpn_type=$(echo "$unblockvpn" | sed 's/-/ /g' | awk '{print $NF}')
vpn_link_up=$(curl -s localhost:79/rci/show/interface/"$vpn_type"/link | tr -d '"')
if [ "$vpn_link_up" = "up" ]; then
add_vpn_mark_rules "$unblockvpn" "$vpn_type"
fi # link

done
fi # check files exist

# если вы хотите использовать какое-то особенное подключение vpn, имейте ввиду unblockvpn* уже используются, используйте другое имя
#if [ -z '$(iptables-save 2>/dev/null | grep unblock-custom-vpn)' ]; then
#	ipset create unblockvpn hash:net -exist

	# С отключением fastnat и ускорителей
	#iptables -I PREROUTING -w -t mangle -p tcp -m set --match-set unblock-custom-vpn dst -j MARK --set-mark 0xd1001
	#iptables -I PREROUTING -w -t mangle -p udp -m set --match-set unblock-custom-vpn dst -j MARK --set-mark 0xd1001

	# только для интерфейса br0
	#iptables -I PREROUTING -w -t mangle -i br0 -p tcp -m set --match-set unblock-custom-vpn dst -j MARK --set-mark 0xd1001
	#iptables -I PREROUTING -w -t mangle -i br0 -p udp -m set --match-set unblock-custom-vpn dst -j MARK --set-mark 0xd1001

	# Без отключения
	#iptables -I PREROUTING -w -t mangle -m conntrack --ctstate NEW -m set --match-set unblock-custom-vpn dst -j CONNMARK --set-mark 0xd1000
	#iptables -I PREROUTING -w -t mangle -j CONNMARK --restore-mark
#fi

exit 0
