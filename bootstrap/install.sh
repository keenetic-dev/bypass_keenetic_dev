#!/bin/sh
set -eu

REPO_OWNER="${BYPASS_REPO_OWNER:-andruwko73}"
REPO_NAME="${BYPASS_REPO_NAME:-bypass_keenetic}"
REPO_BRANCH="${BYPASS_REPO_BRANCH:-main}"
RAW_BASE="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}"

BOT_DIR="/opt/etc/bot"
BOT_CONFIG_PATH="$BOT_DIR/bot_config.py"
BOT_MAIN_PATH="$BOT_DIR/main.py"
INSTALLER_PATH="$BOT_DIR/installer.py"
INSTALLER_ENV_PATH="$BOT_DIR/installer.env"
LEGACY_CONFIG_PATH="/opt/etc/bot_config.py"
LEGACY_MAIN_PATH="/opt/etc/bot.py"
SERVICE_PATH="/opt/etc/init.d/S99telegram_bot"
INSTALLER_SERVICE_PATH="/opt/etc/init.d/S98telegram_bot_installer"
TMP_DIR="/tmp/bypass-bootstrap.$$"
BACKUP_ROOT="/opt/root/bypass-installer-backups"
BACKUP_ID="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_ID"
ABSENT_PATHS_FILE="$BACKUP_DIR/.absent-paths"
ROLLBACK_SCRIPT="$BACKUP_DIR/rollback.sh"
LAST_ROLLBACK_LINK="/opt/root/bypass-last-rollback.sh"

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT INT TERM

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Команда '$1' не найдена"
}

need_var() {
    eval "value=\${$1-}"
    [ -n "$value" ] || fail "Не задана переменная $1"
}

download_file() {
    url="$1"
    target="$2"
    marker="$3"

    curl -fsSL --connect-timeout 20 --retry 2 --retry-delay 1 -o "$target" "$url" || fail "Не удалось скачать $url"
    [ -s "$target" ] || fail "Скачан пустой файл: $url"
    [ -z "$marker" ] || grep -q "$marker" "$target" || fail "Файл $url не прошёл проверку содержимого"
}

ensure_symlink_or_copy() {
    source_path="$1"
    legacy_path="$2"

    rm -f "$legacy_path"
    if ! ln -s "$source_path" "$legacy_path" 2>/dev/null; then
        cp "$source_path" "$legacy_path"
    fi
}

backup_path() {
    source_path="$1"

    if [ -e "$source_path" ] || [ -L "$source_path" ]; then
        mkdir -p "$BACKUP_DIR$(dirname "$source_path")"
        cp -a "$source_path" "$BACKUP_DIR$source_path"
    else
        printf '%s\n' "$source_path" >> "$ABSENT_PATHS_FILE"
    fi
}

write_rollback_script() {
    cat > "$ROLLBACK_SCRIPT" <<EOF
#!/bin/sh
set -eu

BACKUP_DIR='$BACKUP_DIR'
ABSENT_PATHS_FILE='$ABSENT_PATHS_FILE'

restore_path() {
    target_path="\$1"
    backup_path="\$BACKUP_DIR\$target_path"

    if [ -e "\$backup_path" ] || [ -L "\$backup_path" ]; then
        mkdir -p "\$(dirname "\$target_path")"
        rm -rf "\$target_path"
        cp -a "\$backup_path" "\$target_path"
    fi
}

remove_added_path() {
    target_path="\$1"
    if [ -e "\$target_path" ] || [ -L "\$target_path" ]; then
        rm -rf "\$target_path"
    fi
}

restore_path /opt/etc/bot/main.py
restore_path /opt/etc/bot/installer.py
restore_path /opt/etc/bot/installer.env
restore_path /opt/etc/bot.py
restore_path /opt/etc/init.d/S99telegram_bot
restore_path /opt/etc/init.d/S98telegram_bot_installer
restore_path /opt/etc/ndm/fs.d/100-ipset.sh
restore_path /opt/etc/tor/torrc
restore_path /opt/etc/shadowsocks.json
restore_path /opt/etc/init.d/S22shadowsocks
restore_path /opt/etc/xray/config.json
restore_path /opt/etc/v2ray/config.json
restore_path /opt/etc/trojan/config.json
restore_path /opt/etc/init.d/S24xray
restore_path /opt/etc/init.d/S24v2ray
restore_path /opt/bin/unblock_ipset.sh
restore_path /opt/bin/unblock_dnsmasq.sh
restore_path /opt/bin/unblock_update.sh
restore_path /opt/etc/init.d/S99unblock
restore_path /opt/etc/ndm/netfilter.d/100-redirect.sh
restore_path /opt/etc/ndm/ifstatechanged.d/100-unblock-vpn.sh
restore_path /opt/etc/dnsmasq.conf
restore_path /opt/etc/crontab

if [ -f "\$ABSENT_PATHS_FILE" ]; then
    while IFS= read -r added_path; do
        [ -n "\$added_path" ] || continue
        remove_added_path "\$added_path"
    done < "\$ABSENT_PATHS_FILE"
fi

/opt/etc/init.d/S98telegram_bot_installer stop >/dev/null 2>&1 || true
/opt/etc/init.d/S99telegram_bot restart >/dev/null 2>&1 || /opt/etc/init.d/S99telegram_bot start >/dev/null 2>&1 || true
/opt/etc/init.d/S56dnsmasq restart >/dev/null 2>&1 || true
/opt/etc/init.d/S22shadowsocks restart >/dev/null 2>&1 || true
/opt/etc/init.d/S24xray restart >/dev/null 2>&1 || true
/opt/etc/init.d/S24v2ray restart >/dev/null 2>&1 || true
/opt/etc/init.d/S22trojan restart >/dev/null 2>&1 || true
/opt/etc/init.d/S35tor restart >/dev/null 2>&1 || true
/opt/etc/init.d/S99unblock restart >/dev/null 2>&1 || true

echo "Rollback completed from \$BACKUP_DIR"
EOF

    chmod 700 "$ROLLBACK_SCRIPT"
    rm -f "$LAST_ROLLBACK_LINK"
    ln -s "$ROLLBACK_SCRIPT" "$LAST_ROLLBACK_LINK" 2>/dev/null || cp "$ROLLBACK_SCRIPT" "$LAST_ROLLBACK_LINK"
}

detect_router_ip() {
    detected_ip=$(ip -4 addr show br0 2>/dev/null | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -n1 || true)
    if [ -n "$detected_ip" ]; then
        printf '%s' "$detected_ip"
    else
        printf '%s' '192.168.1.1'
    fi
}

if [ "$(id -u)" -ne 0 ]; then
    fail "Запустите bootstrap от root на роутере"
fi

need_cmd curl
need_cmd grep
need_cmd sed
need_cmd mkdir

if [ ! -x /opt/bin/opkg ] && ! command -v opkg >/dev/null 2>&1; then
    echo "Entware не найден в /opt." >&2
    echo "Этот bootstrap убирает ручную SSH-установку, но не отменяет подготовку хранилища для Entware на Keenetic." >&2
    echo "Сначала подготовьте накопитель и установите Entware, затем повторите запуск bootstrap." >&2
    exit 2
fi

mkdir -p "$TMP_DIR" "$BOT_DIR"
mkdir -p "$BACKUP_DIR"
: > "$ABSENT_PATHS_FILE"

ROUTER_IP="${BYPASS_ROUTER_IP:-$(detect_router_ip)}"
BROWSER_PORT="${BYPASS_BROWSER_PORT:-8080}"
DEFAULT_PROXY_MODE="${BYPASS_DEFAULT_PROXY_MODE:-none}"
FORK_BUTTON_LABEL="${BYPASS_FORK_BUTTON_LABEL:-Fork by ${REPO_OWNER}}"

backup_path "$BOT_MAIN_PATH"
backup_path "$INSTALLER_PATH"
backup_path "$INSTALLER_ENV_PATH"
backup_path "$LEGACY_MAIN_PATH"
backup_path "$SERVICE_PATH"
backup_path "$INSTALLER_SERVICE_PATH"
backup_path "/opt/etc/ndm/fs.d/100-ipset.sh"
backup_path "/opt/etc/tor/torrc"
backup_path "/opt/etc/shadowsocks.json"
backup_path "/opt/etc/init.d/S22shadowsocks"
backup_path "/opt/etc/xray/config.json"
backup_path "/opt/etc/v2ray/config.json"
backup_path "/opt/etc/trojan/config.json"
backup_path "/opt/etc/init.d/S24xray"
backup_path "/opt/etc/init.d/S24v2ray"
backup_path "/opt/bin/unblock_ipset.sh"
backup_path "/opt/bin/unblock_dnsmasq.sh"
backup_path "/opt/bin/unblock_update.sh"
backup_path "/opt/etc/init.d/S99unblock"
backup_path "/opt/etc/ndm/netfilter.d/100-redirect.sh"
backup_path "/opt/etc/ndm/ifstatechanged.d/100-unblock-vpn.sh"
backup_path "/opt/etc/dnsmasq.conf"
backup_path "/opt/etc/crontab"
write_rollback_script

download_file "$RAW_BASE/script.sh" "$TMP_DIR/script.sh" 'if \[ "$1" = "-install" \]; then'
download_file "$RAW_BASE/bot.py" "$TMP_DIR/main.py" 'KeyInstallHTTPRequestHandler'
download_file "$RAW_BASE/installer.py" "$TMP_DIR/installer.py" 'ThreadingHTTPServer'
download_file "$RAW_BASE/S99telegram_bot" "$TMP_DIR/S99telegram_bot" 'Bot started successfully'
download_file "$RAW_BASE/S98telegram_bot_installer" "$TMP_DIR/S98telegram_bot_installer" 'Installer started successfully'

cp "$TMP_DIR/main.py" "$BOT_MAIN_PATH"
cp "$TMP_DIR/installer.py" "$INSTALLER_PATH"
cp "$TMP_DIR/S99telegram_bot" "$SERVICE_PATH"
cp "$TMP_DIR/S98telegram_bot_installer" "$INSTALLER_SERVICE_PATH"

chmod 755 "$TMP_DIR/script.sh" "$BOT_MAIN_PATH" "$INSTALLER_PATH" "$SERVICE_PATH" "$INSTALLER_SERVICE_PATH"
ensure_symlink_or_copy "$BOT_MAIN_PATH" "$LEGACY_MAIN_PATH"

/bin/sh "$TMP_DIR/script.sh" -install

if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_USERNAME:-}" ] && [ -n "${TG_APP_API_ID:-}" ] && [ -n "${TG_APP_API_HASH:-}" ]; then
    cat > "$BOT_CONFIG_PATH" <<EOF
# ВЕРСИЯ СКРИПТА 2.2.0

token = '${TG_BOT_TOKEN}'
usernames = ['${TG_USERNAME}']

appapiid = '${TG_APP_API_ID}'
appapihash = '${TG_APP_API_HASH}'
routerip = '${ROUTER_IP}'
browser_port = '${BROWSER_PORT}'
fork_repo_owner = '${REPO_OWNER}'
fork_repo_name = '${REPO_NAME}'
fork_button_label = '${FORK_BUTTON_LABEL}'

vpn_allowed="IKE|SSTP|OpenVPN|Wireguard|L2TP"

localportsh = '1082'
dnsporttor = '9053'
localporttor = '9141'
localportvmess = '10810'
localportvless = '10811'
localporttrojan = '10829'
default_proxy_mode = '${DEFAULT_PROXY_MODE}'
dnsovertlsport = '40500'
dnsoverhttpsport = '40508'
EOF
    chmod 600 "$BOT_CONFIG_PATH"
    rm -f "$INSTALLER_ENV_PATH"
    ensure_symlink_or_copy "$BOT_CONFIG_PATH" "$LEGACY_CONFIG_PATH"
    "$INSTALLER_SERVICE_PATH" stop >/dev/null 2>&1 || true
    "$SERVICE_PATH" restart || "$SERVICE_PATH" start || fail "Не удалось запустить сервис бота"
    echo "Bootstrap-установка завершена."
    echo "Веб-интерфейс: http://${ROUTER_IP}:${BROWSER_PORT}/"
    echo "Проверка сервиса: $SERVICE_PATH status"
    echo "Откат: $ROLLBACK_SCRIPT"
    exit 0
fi

cat > "$INSTALLER_ENV_PATH" <<EOF
BYPASS_INSTALLER_PORT=${BROWSER_PORT}
EOF
chmod 644 "$INSTALLER_ENV_PATH"

# Force true first-run installer mode: existing bot_config would prevent
# S98telegram_bot_installer from starting and leave the previous bot token active.
rm -f "$BOT_CONFIG_PATH" "$LEGACY_CONFIG_PATH"

"$SERVICE_PATH" stop >/dev/null 2>&1 || true
"$INSTALLER_SERVICE_PATH" restart || "$INSTALLER_SERVICE_PATH" start || fail "Не удалось запустить web installer"

echo "Bootstrap-установка завершена в режиме первичной настройки."
echo "Откройте страницу: http://${ROUTER_IP}:${BROWSER_PORT}/"
echo "После сохранения формы installer сам запустит основной бот."
echo "Откат: $ROLLBACK_SCRIPT"