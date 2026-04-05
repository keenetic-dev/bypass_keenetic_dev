#!/bin/sh

REPO="keenetic-dev"
BRANCH="bypass_keenetic_dev"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/refs/heads/dev"
BACKUP_DIR="/opt/etc/.backup_bypass"

FILES="
/opt/etc/ndm/fs.d/100-ipset.sh:100-ipset.sh
/opt/etc/ndm/netfilter.d/100-redirect.sh:100-redirect.sh
/opt/bin/unblock_dnsmasq.sh:unblock.dnsmasq
/opt/bin/unblock_ipset.sh:unblock_ipset.sh
/opt/bin/unblock_update.sh:unblock_update.sh
/opt/etc/unblock/router.txt:unblockrouter.txt
"

update_all() {
    echo "--- Starting Update ---"
    # Создаем папку бэкапа, если её нет
    mkdir -p "$BACKUP_DIR"
    touch /opt/etc/unblock/router.txt
    chmod 0755 /opt/etc/unblock/router.txt

    for item in $FILES; do
        LOCAL=$(echo $item | cut -d: -f1)
        REMOTE=$(echo $item | cut -d: -f2)
        FILE_NAME=$(basename "$LOCAL")

        echo "Updating: $FILE_NAME"

        # Перемещаем старый файл в бэкап
        if [ -f "$LOCAL" ]; then
            mv "$LOCAL" "${BACKUP_DIR}/${FILE_NAME}"
            # На всякий случай снимаем права на выполнение в бэкапе
            chmod -x "${BACKUP_DIR}/${FILE_NAME}"
        fi

        # Качаем новый
        curl -sSL -o "$LOCAL" "${BASE_URL}/${REMOTE}"

        if [ $? -eq 0 ]; then
            chmod +x "$LOCAL"
            chmod 0755 "$LOCAL"
            echo "Successfully updated $FILE_NAME"
        else
            echo "Error downloading $FILE_NAME! Restoring from backup..."
            [ -f "${BACKUP_DIR}/${FILE_NAME}" ] && mv "${BACKUP_DIR}/${FILE_NAME}" "$LOCAL" && chmod +x "$LOCAL"
        fi
    done
    echo "--- Update Complete ---"
}

rollback_all() {
    echo "--- Rolling back from $BACKUP_DIR ---"
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "Backup directory not found!"
        exit 1
    fi

    for item in $FILES; do
        LOCAL=$(echo $item | cut -d: -f1)
        FILE_NAME=$(basename "$LOCAL")

        if [ -f "${BACKUP_DIR}/${FILE_NAME}" ]; then
            mv "${BACKUP_DIR}/${FILE_NAME}" "$LOCAL"
            chmod +x "$LOCAL"
            chmod 0755 "$LOCAL"
            echo "Restored: $FILE_NAME"
        else
            echo "No backup found for: $FILE_NAME"
        fi
    done
    echo "--- Rollback Complete ---"
}

case "$1" in
    update) update_all ;;
    rollback) rollback_all ;;
    *) echo "Usage: curl https://raw.githubusercontent.com/keenetic-dev/bypass_keenetic_dev/refs/heads/dev/install.sh | sh -s {update|rollback}"; exit 1 ;;
esac
