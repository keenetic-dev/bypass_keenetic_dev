# ВЕРСИЯ СКРИПТА 2.2.0

token = 'MyBotFatherToken'  # ключ api бота
usernames = ['MySuperLogin']  # Ваш логин в телеграмме без @, не бота. Логин именно Вашей учетной записи в ТГ.

# следующие две строки заполняются с сайта https://my.telegram.org/apps
# вместо вас запрос будет посылать бот, оттуда и будут запрашиваться ключи
appapiid = 'myapiid'
appapihash = 'myiphash'
routerip = '192.168.1.1'  # ip роутера
browser_port = '8080'  # порт для веб-интерфейса установки ключей
fork_repo_owner = 'andruwko73'  # GitHub username вашего форка bypass_keenetic
fork_repo_name = 'bypass_keenetic'  # имя репозитория форка
fork_button_label = 'Fork by andruwko73'  # подпись кнопки установки из вашего форка

# список vpn для выборочной маршрутизации
vpn_allowed="IKE|SSTP|OpenVPN|Wireguard|L2TP"

# следующие настройки могут быть оставлены по умолчанию, но можно будет что-то поменять
localportsh = '1082'  # локальный порт для shadowsocks
dnsporttor = '9053'  # чтобы onion сайты открывался через любой браузер - любой открытый порт
localporttor = '9141'  # локальный порт для тор
localportvmess = '10810'  # локальный порт для vmess
localportvless = '10811'  # локальный порт для vless
localporttrojan = '10829'  # локальный порт для trojan
default_proxy_mode = 'none'  # выбор прокси для Telegram API: none, shadowsocks, vmess, vless, trojan
dnsovertlsport = '40500'  # можно посмотреть номер порта командой "cat /tmp/ndnproxymain.stat"
dnsoverhttpsport = '40508'  # можно посмотреть номер порта командой "cat /tmp/ndnproxymain.stat"

# ЕСЛИ ВЫ ХОТИТЕ ПОДДЕРЖАТЬ РАЗРАБОТЧИКОВ - МОЖЕТЕ ОТПРАВИТЬ ДОНАТ НА ЛЮБУЮ СУММУ
# znetworkx aka NetworK - 4817 7603 0990 8527 (Сбербанк VISA)
# tas-unn aka Materland - 2204 1201 0098 8217 (КАРТА МИР)
