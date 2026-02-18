#!/bin/bash

# Даем права на выполнение самому скрипту (если они не были установлены)
chmod +x $0

# Функция для обновления бота
update_bot() {
    echo "Updating bot..."
    opkg update
    opkg update trojan
    mv /opt/etc/bot.py /opt/etc/bot_old.py
    curl -o /opt/etc/bot.py https://raw.githubusercontent.com/keenetic-dev/bypass_keenetic_dev/refs/heads/dev/bot.py
    bot_pid=$(ps | grep bot.py | awk '{print $1}')
    for bot in ${bot_pid}; do kill "${bot}"; done
    python3 /opt/etc/bot.py &
    if [ $? -eq 0 ]; then
        echo "Bot started successfully!"
    else
        bot_pid=$(ps | grep bot.py | awk '{print $1}')
        for bot in ${bot_pid}; do kill "${bot}"; done
        mv /opt/etc/bot_old.py /opt/etc/bot.py
        python3 /opt/etc/bot.py
        echo "Bot not working, rolled back to the old version"
    fi
}

# Функция для отката
rollback_bot() {
    echo "Rolling back to the old bot version..."
    bot_pid=$(ps | grep bot.py | awk '{print $1}')
    for bot in ${bot_pid}; do kill "${bot}"; done
    mv /opt/etc/bot_old.py /opt/etc/bot.py
    python3 /opt/etc/bot.py &
    echo "Manually rolled back to the old bot.py"
}

# Проверяем аргумент для выполнения соответствующей команды
case "$1" in
    update)
        update_bot
        ;;
    rollback)
        rollback_bot
        ;;
    *)
        echo "Usage: $0 {update|rollback}"
        exit 1
        ;;
esac
