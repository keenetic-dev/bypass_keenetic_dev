<a href="https://t.me/bypass_keenetic">![Telegram](https://img.shields.io/badge/bypass_keenetic--black?style=social&logo=telegram&logoColor=blue)</a>

## Об этом форке
Это форк проекта `keenetic-dev/bypass_keenetic_dev`.

В текущем форке добавлены:
- веб-интерфейс установки ключей и мостов
- выбор маршрутизации Telegram через локальный VPN/прокси
- поддержка VLESS вместе с Shadowsocks, Trojan и Vmess
- поддержка двух отдельных маршрутов VLESS с разными ключами и списками сайтов
- обновления управления через Telegram-бота

## Установка обхода блокировок на роутерах Keenetic с установленной средой Entware, управление через телеграм бот.

## Что это и зачем
- [Полное описание читайте в оригинальной вики](https://github.com/znetworkx/bypass_keenetic/wiki)

## Возможности и преимущества
- открытые исходники, полностью **бесплатно**
- управление **через ВАШ телеграм бот** (да, у вас будет свой бот :-)
- поддержка vpn (wireguard, sstp, l2tp, etc)
- поддержка shadowsocks, tor
- **все устройста подключенные к вашему Keenetic смогут открывать сайты из списка** (tv, phone, pc, tablet, etc)!
- можно подключаться к роутеру из вне по vpn и обход будет работать даже если вы не дома
- удобное обновление ключей и списка адресов
- **безопасная маршрутизация**, трафик vpn идет только к тем сайтам, что указаны в списках, вы спокойно можете использовать госуслуги, интернет-банки (**безопасно!**)
- дальнейшее обновление одним кликом
- поддержка на [форуме](https://forum.keenetic.com/topic/14672-%D0%BE%D0%B1%D1%85%D0%BE%D0%B4%D0%B0-%D0%B1%D0%BB%D0%BE%D0%BA%D0%B8%D1%80%D0%BE%D0%B2%D0%BE%D0%BA-%D0%BC%D0%BD%D0%BE%D0%B3%D0%BE-%D0%BD%D0%B5-%D0%B1%D1%8B%D0%B2%D0%B0%D0%B5%D1%82) и [чате телеграм](https://t.me/bypass_keenetic)

## Установка (~30-60 минут с нуля)
- [Установка Entware](https://github.com/znetworkx/bypass_keenetic/wiki/Install-Entware-and-Preparation)
- [Установка бота и скриптов](https://github.com/znetworkx/bypass_keenetic/wiki/Install-bot-and-scripts)


## Шаблоны списков
- [vless-2.txt](vless-2.txt) — готовый шаблон списка доменов для второго маршрута VLESS, собранный под GitHub Copilot, GitHub и связанную инфраструктуру VS Code/Microsoft.
