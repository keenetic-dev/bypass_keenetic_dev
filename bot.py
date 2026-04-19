#!/usr/bin/python3

#  2023. Keenetic DNS bot /  Проект: bypass_keenetic / Автор: tas_unn
#  GitHub: https://github.com/tas-unn/bypass_keenetic
#  Данный бот предназначен для управления обхода блокировок на роутерах Keenetic
#  Демо-бот: https://t.me/keenetic_dns_bot
#
#  Файл: bot.py, Версия 2.2.1, последнее изменение: 02.10.2023, 00:55
#  Доработал: NetworK (https://github.com/znetworkx)

# ВЕРСИЯ СКРИПТА 2.2.1
# ЕСЛИ ВЫ ХОТИТЕ ПОДДЕРЖАТЬ РАЗРАБОТЧИКОВ - МОЖЕТЕ ОТПРАВИТЬ ДОНАТ НА ЛЮБУЮ СУММУ
# znetworkx aka NetworK - 4817 7603 0990 8527 (Сбербанк VISA)
# tas-unn aka Materland - 2204 1201 0098 8217 (КАРТА МИР)

import asyncio
import subprocess
import os
import re
import stat
import sys
import time
import threading
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import telebot
from telebot import types
from telethon.sync import TelegramClient
import base64
# from pathlib import Path
import shutil
# import datetime
import requests
import json
import html
import bot_config as config

token = config.token
appapiid = config.appapiid
appapihash = config.appapihash
usernames = config.usernames
routerip = config.routerip
browser_port = config.browser_port
fork_repo_owner = getattr(config, 'fork_repo_owner', 'andruwko73')
fork_repo_name = getattr(config, 'fork_repo_name', 'bypass_keenetic')
fork_button_label = getattr(config, 'fork_button_label', f'Fork by {fork_repo_owner}')
localportsh = config.localportsh
localporttor = config.localporttor
localporttrojan = config.localporttrojan
localportvmess = config.localportvmess
localportvless = config.localportvless
localportvless_transparent = str(int(localportvless) + 1)
localportsh_bot = str(getattr(config, 'localportsh_bot', 10820))
localporttrojan_bot = str(getattr(config, 'localporttrojan_bot', 10830))
dnsporttor = config.dnsporttor
dnsovertlsport = config.dnsovertlsport
dnsoverhttpsport = config.dnsoverhttpsport

# Начало работы программы
bot = telebot.TeleBot(token)
level = 0
bypass = -1
sid = "0"
PROXY_MODE_FILE = '/opt/etc/bot_proxy_mode'
BOT_AUTOSTART_FILE = '/opt/etc/bot_autostart'
WEB_STATUS_CACHE_TTL = 20
KEY_STATUS_CACHE_TTL = 20
BOT_SOURCE_PATH = os.path.abspath(__file__)
XRAY_SERVICE_SCRIPT = '/opt/etc/init.d/S24xray'
V2RAY_SERVICE_SCRIPT = '/opt/etc/init.d/S24v2ray'
XRAY_CONFIG_DIR = '/opt/etc/xray'
V2RAY_CONFIG_DIR = '/opt/etc/v2ray'
CORE_PROXY_CONFIG_DIR = XRAY_CONFIG_DIR if os.path.exists(XRAY_SERVICE_SCRIPT) else V2RAY_CONFIG_DIR
CORE_PROXY_SERVICE_SCRIPT = XRAY_SERVICE_SCRIPT if os.path.exists(XRAY_SERVICE_SCRIPT) else V2RAY_SERVICE_SCRIPT
CORE_PROXY_CONFIG_PATH = os.path.join(CORE_PROXY_CONFIG_DIR, 'config.json')
CORE_PROXY_ERROR_LOG = os.path.join(CORE_PROXY_CONFIG_DIR, 'error.log')
CORE_PROXY_ACCESS_LOG = os.path.join(CORE_PROXY_CONFIG_DIR, 'access.log')
VMESS_KEY_PATH = os.path.join(CORE_PROXY_CONFIG_DIR, 'vmess.key')
VLESS_KEY_PATH = os.path.join(CORE_PROXY_CONFIG_DIR, 'vless.key')

bot_ready = False
bot_polling = False
proxy_mode = config.default_proxy_mode
proxy_settings = {
    'none': None,
    'shadowsocks': f'socks5h://127.0.0.1:{localportsh_bot}',
    'vmess': f'socks5h://127.0.0.1:{localportvmess}',
    'vless': f'socks5h://127.0.0.1:{localportvless}',
    'trojan': f'socks5h://127.0.0.1:{localporttrojan_bot}',
}
proxy_supports_http = {
    'none': True,
    'shadowsocks': True,
    'vmess': True,
    'vless': True,
    'trojan': True,
}
web_status_cache = {
    'timestamp': 0,
    'data': None,
}
key_status_cache = {
    'timestamp': 0,
    'data': None,
    'signature': None,
}
web_command_lock = threading.Lock()
web_command_state = {
    'running': False,
    'command': '',
    'label': '',
    'result': '',
    'started_at': 0,
    'finished_at': 0,
}
web_flash_lock = threading.Lock()
web_flash_message = ''


def _raw_github_url(path):
    return f'https://raw.githubusercontent.com/{fork_repo_owner}/{fork_repo_name}/main/{path}?ts={int(time.time())}'


def _has_socks_support():
    try:
        import socks  # noqa: F401
        return True
    except Exception:
        return False


def _daemonize_process():
    if os.name != 'posix':
        return
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
    except Exception:
        pass


def _save_proxy_mode(proxy_type):
    try:
        os.makedirs(os.path.dirname(PROXY_MODE_FILE), exist_ok=True)
        with open(PROXY_MODE_FILE, 'w', encoding='utf-8') as file:
            file.write(proxy_type)
    except Exception:
        pass


def _proxy_mode_label(proxy_type):
    labels = {
        'none': 'None',
        'shadowsocks': 'Shadowsocks',
        'vmess': 'Vmess',
        'vless': 'Vless',
        'trojan': 'Trojan',
    }
    return labels.get(proxy_type, proxy_type)


def _save_bot_autostart(enabled):
    try:
        if enabled:
            with open(BOT_AUTOSTART_FILE, 'w', encoding='utf-8') as file:
                file.write('1')
        elif os.path.exists(BOT_AUTOSTART_FILE):
            os.remove(BOT_AUTOSTART_FILE)
    except Exception:
        pass


def _prepare_entware_dns():
    try:
        result = subprocess.run(
            ['nslookup', 'bin.entware.net', '192.168.1.1'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return 'Entware DNS уже доступен.'
    except Exception:
        pass

    notes = []
    try:
        subprocess.run(['ndmc', '-c', 'no opkg dns-override'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(['ndmc', '-c', 'system configuration save'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        notes.append('opkg dns-override отключён')
    except Exception:
        notes.append('не удалось отключить opkg dns-override')

    try:
        resolv_conf = '/etc/resolv.conf'
        preserved_lines = []
        if os.path.exists(resolv_conf):
            with open(resolv_conf, 'r', encoding='utf-8', errors='ignore') as file:
                preserved_lines = [
                    line.rstrip('\n')
                    for line in file
                    if line.strip() and not line.lstrip().startswith('nameserver')
                ]
        with open(resolv_conf, 'w', encoding='utf-8') as file:
            file.write('nameserver 8.8.8.8\n')
            file.write('nameserver 1.1.1.1\n')
            if preserved_lines:
                file.write('\n'.join(preserved_lines) + '\n')
        notes.append('внешние DNS записаны первыми в /etc/resolv.conf')
    except Exception:
        notes.append('не удалось обновить /etc/resolv.conf')

    try:
        lookup_output = subprocess.check_output(
            ['nslookup', 'bin.entware.net', '8.8.8.8'],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        host_matches = re.findall(r'Address\s+\d+:\s+((?:\d{1,3}\.){3}\d{1,3})', lookup_output)
        entware_ip = host_matches[-1] if host_matches else ''
        if entware_ip:
            hosts_path = '/etc/hosts'
            preserved_lines = []
            if os.path.exists(hosts_path):
                with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as file:
                    preserved_lines = [line.rstrip('\n') for line in file if 'bin.entware.net' not in line]
            with open(hosts_path, 'w', encoding='utf-8') as file:
                if preserved_lines:
                    file.write('\n'.join(preserved_lines) + '\n')
                file.write(f'{entware_ip} bin.entware.net\n')
            notes.append(f'bin.entware.net закреплён в /etc/hosts как {entware_ip}')
    except Exception:
        notes.append('не удалось закрепить bin.entware.net в /etc/hosts')

    return 'Подготовка Entware DNS: ' + ', '.join(notes)


def _ensure_legacy_bot_paths():
    mappings = [
        ('/opt/etc/bot/bot_config.py', '/opt/etc/bot_config.py'),
        ('/opt/etc/bot/main.py', '/opt/etc/bot.py'),
    ]
    notes = []
    for source_path, legacy_path in mappings:
        try:
            if not os.path.exists(source_path):
                continue
            if os.path.islink(legacy_path):
                if os.path.realpath(legacy_path) == os.path.realpath(source_path):
                    continue
                os.remove(legacy_path)
            elif os.path.exists(legacy_path):
                continue
            os.symlink(source_path, legacy_path)
            notes.append(f'{legacy_path} -> {source_path}')
        except Exception:
            try:
                shutil.copyfile(source_path, legacy_path)
                notes.append(f'{legacy_path} скопирован из {source_path}')
            except Exception:
                notes.append(f'не удалось подготовить {legacy_path}')
    if not notes:
        return 'Legacy-пути бота уже доступны.'
    return 'Подготовка legacy-путей: ' + ', '.join(notes)


def _chunk_text(text, limit=3500):
    if not text or not text.strip():
        return []
    chunks = []
    current = []
    current_len = 0
    for line in text.splitlines():
        extra = len(line) + 1
        if current and current_len + extra > limit:
            chunks.append('\n'.join(current))
            current = [line]
            current_len = extra
        else:
            current.append(line)
            current_len += extra
    if current:
        chunks.append('\n'.join(current))
    return chunks or ['']


def _send_telegram_chunks(chat_id, text, reply_markup=None):
    for chunk in _chunk_text(text):
        if not chunk.strip():
            continue
        bot.send_message(chat_id, chunk, reply_markup=reply_markup)


def _install_proxy_from_message(message, key_type, key_value, reply_markup):
    installers = {
        'shadowsocks': shadowsocks,
        'vmess': vmess,
        'vless': vless,
        'trojan': trojan,
    }
    try:
        installers[key_type](key_value)
        result = _apply_installed_proxy(key_type, key_value)
    except Exception as exc:
        result = f'Ошибка установки: {exc}'

    level_reset_markup = reply_markup
    try:
        bot.send_message(message.chat.id, result, reply_markup=level_reset_markup)
    except Exception:
        fallback_result = (
            f'{result}\n\n'
            'Текущий режим бота сохранён, но отправить подтверждение в этот чат не удалось.'
        )
        try:
            bot.send_message(message.chat.id, fallback_result, reply_markup=level_reset_markup)
        except Exception:
            pass
    return result


def _download_repo_script(repo_owner, repo_name):
    url = f'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main/script.sh'
    response = requests.get(
        url,
        params={'ts': str(int(time.time()))},
        headers={'Cache-Control': 'no-cache', 'Pragma': 'no-cache'},
        timeout=30,
    )
    response.raise_for_status()
    script_text = response.text
    if '#!/bin/sh' not in script_text:
        raise ValueError('GitHub вернул некорректный script.sh')
    with open('/opt/root/script.sh', 'w', encoding='utf-8') as file:
        file.write(script_text)
    os.chmod('/opt/root/script.sh', stat.S_IRWXU)
    return url, script_text


def _run_script_action(action, repo_owner=None, repo_name=None):
    logs = [_prepare_entware_dns(), _ensure_legacy_bot_paths()]
    if repo_owner and repo_name:
        url, script_text = _download_repo_script(repo_owner, repo_name)
        logs.append(f'Скрипт загружен из {url}')
        if repo_owner == fork_repo_owner and 'BOT_CONFIG_PATH' not in script_text:
            logs.append('⚠️ GitHub отдал старую версию script.sh, но legacy-пути уже подготовлены на роутере.')

    process = subprocess.Popen(
        ['/bin/sh', '/opt/root/script.sh', action],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in process.stdout:
        clean_line = line.strip()
        if clean_line:
            logs.append(clean_line)
    return_code = process.wait()
    if return_code != 0:
        logs.append(f'Команда завершилась с кодом {return_code}.')
    return return_code, '\n'.join(logs)


def _restart_router_services():
    commands = [
        '/opt/etc/init.d/S56dnsmasq restart',
        '/opt/etc/init.d/S22shadowsocks restart',
        CORE_PROXY_SERVICE_SCRIPT + ' restart',
        '/opt/etc/init.d/S22trojan restart',
        '/opt/etc/init.d/S35tor restart',
    ]
    for command in commands:
        os.system(command)
    _invalidate_web_status_cache()
    return '✅ Сервисы перезагружены.'


def _set_dns_override(enabled):
    if enabled:
        os.system("ndmc -c 'opkg dns-override'")
        time.sleep(2)
        os.system("ndmc -c 'system configuration save'")
        return '✅ DNS Override включен. Для применения роутер будет перезагружен.'
    os.system("ndmc -c 'no opkg dns-override'")
    time.sleep(2)
    os.system("ndmc -c 'system configuration save'")
    return '✅ DNS Override выключен. Для применения роутер будет перезагружен.'


def _run_web_command(command):
    if command == 'install_original':
        _, output = _run_script_action('-install', 'tas-unn', 'bypass_keenetic')
        return output
    if command == 'install_fork':
        _, output = _run_script_action('-install', fork_repo_owner, fork_repo_name)
        return output
    if command == 'update':
        _, output = _run_script_action('-update', fork_repo_owner, fork_repo_name)
        return output
    if command == 'remove':
        _, output = _run_script_action('-remove', fork_repo_owner, fork_repo_name)
        return output
    if command == 'restart_services':
        return _restart_router_services()
    if command == 'dns_on':
        return _set_dns_override(True)
    if command == 'dns_off':
        return _set_dns_override(False)
    if command == 'reboot':
        os.system('ndmc -c system reboot')
        return '🔄 Роутер перезагружается. Это займёт около 2 минут.'
    return 'Команда не распознана.'


def _read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception:
        return ''


def _normalize_unblock_list(text):
    items = []
    seen = set()
    for raw_line in text.replace('\r', '\n').split('\n'):
        line = raw_line.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        items.append(line)
    items.sort()
    return '\n'.join(items)


def _save_unblock_list(list_name, text):
    safe_name = os.path.basename(list_name)
    target_path = os.path.join('/opt/etc/unblock', safe_name)
    if not target_path.endswith('.txt'):
        raise ValueError('Список должен быть .txt файлом')
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    normalized = _normalize_unblock_list(text)
    with open(target_path, 'w', encoding='utf-8') as file:
        if normalized:
            file.write(normalized + '\n')
    subprocess.call(['/opt/bin/unblock_update.sh'])
    return f'✅ Список {safe_name} сохранён и применён.'


def _append_socialnet_list(list_name):
    safe_name = os.path.basename(list_name)
    target_path = os.path.join('/opt/etc/unblock', safe_name)
    current = _read_text_file(target_path)
    social_text = requests.get('https://raw.githubusercontent.com/tas-unn/bypass_keenetic/main/socialnet.txt', timeout=20).text
    return _save_unblock_list(safe_name, current + '\n' + social_text)


def _list_label(file_name):
    base = file_name[:-4] if file_name.endswith('.txt') else file_name
    labels = {
        'shadowsocks': 'Shadowsocks',
        'tor': 'Tor',
        'vmess': 'Vmess',
        'vless': 'Vless',
        'trojan': 'Trojan',
        'vpn': 'VPN (общий список)',
    }
    if base.startswith('vpn-'):
        return f'VPN: {base[4:]}'
    return labels.get(base, base)


def _load_unblock_lists():
    unblock_dir = '/opt/etc/unblock'
    try:
        file_names = sorted(name for name in os.listdir(unblock_dir) if name.endswith('.txt'))
    except Exception:
        file_names = []
    file_names = [name for name in file_names if name not in ['vpn.txt', 'tor.txt']]
    preferred_order = ['vless.txt', 'vmess.txt', 'trojan.txt', 'shadowsocks.txt', 'vpn.txt', 'tor.txt']
    ordered = []
    for item in preferred_order:
        if item in file_names:
            ordered.append(item)
    for item in file_names:
        if item not in ordered:
            ordered.append(item)
    result = []
    for file_name in ordered:
        result.append({
            'name': file_name,
            'label': _list_label(file_name),
            'content': _read_text_file(os.path.join(unblock_dir, file_name)).strip(),
        })
    return result


def _transparent_list_route_label():
    config_text = _read_text_file(CORE_PROXY_CONFIG_PATH)
    if 'in-vless-transparent' in config_text and 'proxy-vless' in config_text:
        return 'Vless'
    return 'Не определён'


def _load_shadowsocks_key():
    try:
        with open('/opt/etc/shadowsocks.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        server = (data.get('server') or [''])[0]
        port = data.get('server_port', '')
        method = data.get('method', '')
        password = data.get('password', '')
        if not server or not port or not method:
            return ''
        encoded = base64.urlsafe_b64encode(f'{method}:{password}'.encode('utf-8')).decode('utf-8').rstrip('=')
        return f'ss://{encoded}@{server}:{port}'
    except Exception:
        return ''


def _load_trojan_key():
    try:
        with open('/opt/etc/trojan/config.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        password = (data.get('password') or [''])[0]
        address = data.get('remote_addr', '')
        port = data.get('remote_port', '')
        if not password or not address or not port:
            return ''
        return f'trojan://{password}@{address}:{port}'
    except Exception:
        return ''


def _load_tor_bridges():
    lines = []
    for line in _read_text_file('/opt/etc/tor/torrc').splitlines():
        stripped = line.strip()
        if stripped.startswith('Bridge '):
            lines.append(stripped)
    return '\n'.join(lines)


def _load_current_keys():
    return {
        'shadowsocks': _load_shadowsocks_key(),
        'vmess': _read_v2ray_key(VMESS_KEY_PATH) or '',
        'vless': _read_v2ray_key(VLESS_KEY_PATH) or '',
        'trojan': _load_trojan_key(),
    }


def _invalidate_key_status_cache():
    key_status_cache['timestamp'] = 0
    key_status_cache['data'] = None
    key_status_cache['signature'] = None


def _check_http_through_proxy(proxy_url, url='https://www.youtube.com', connect_timeout=4, read_timeout=6):
    try:
        response = requests.get(
            url,
            timeout=(connect_timeout, read_timeout),
            proxies={'https': proxy_url, 'http': proxy_url},
            stream=True,
        )
        status_code = response.status_code
        response.close()
        if status_code < 500:
            return True, f'Веб-доступ через ключ подтверждён (HTTP {status_code}).'
        return False, f'Веб-проверка через ключ вернула HTTP {status_code}.'
    except requests.exceptions.ConnectTimeout:
        return False, 'Прокси не установил соединение за отведённое время.'
    except requests.exceptions.ReadTimeout:
        return False, 'Удалённый сервер не ответил вовремя через этот ключ.'
    except requests.exceptions.RequestException as exc:
        return False, f'Веб-проверка через ключ завершилась ошибкой: {exc}'


def _check_telegram_api_through_proxy(proxy_url=None, connect_timeout=6, read_timeout=10):
    url = f'https://api.telegram.org/bot{token}/getMe'
    proxies = {'https': proxy_url, 'http': proxy_url} if proxy_url else None
    try:
        response = requests.get(url, timeout=(connect_timeout, read_timeout), proxies=proxies)
        response.raise_for_status()
        data = response.json()
        if data.get('ok'):
            return True, 'Доступ к api.telegram.org подтверждён.'
        return False, f'Telegram API ответил: {data.get("description", "Не удалось определить причину")}.'
    except requests.exceptions.ConnectTimeout:
        return False, 'Прокси не установил соединение с api.telegram.org за отведённое время.'
    except requests.exceptions.ReadTimeout:
        return False, 'Сервер Telegram не ответил вовремя через этот ключ.'
    except requests.exceptions.RequestException as exc:
        error_text = str(exc)
        if 'Missing dependencies for SOCKS support' in error_text:
            return False, 'Отсутствует поддержка SOCKS (PySocks) для проверки Telegram API.'
        return False, f'Проверка Telegram API завершилась ошибкой: {exc}'


def _protocol_status_for_key(key_name, key_value):
    if not key_value.strip():
        return {
            'tone': 'empty',
            'label': 'Не сохранён',
            'details': 'Ключ ещё не сохранён на роутере.',
        }
    ports = {
        'shadowsocks': localportsh_bot,
        'vmess': localportvmess,
        'vless': localportvless,
        'trojan': localporttrojan_bot,
    }
    port = ports.get(key_name)
    endpoint_ok, endpoint_message = _check_local_proxy_endpoint(key_name, port)
    if not endpoint_ok:
        return {
            'tone': 'fail',
            'label': 'Не работает',
            'details': f'{endpoint_message} Бот не может использовать этот ключ.',
        }

    proxy_url = proxy_settings.get(key_name)
    api_ok, api_message = _check_http_through_proxy(
        proxy_url,
        url='https://api.telegram.org',
        connect_timeout=3,
        read_timeout=4,
    )
    return {
        'tone': 'ok' if api_ok else 'fail',
        'label': 'Работает' if api_ok else 'Не работает',
        'details': f'{endpoint_message} {api_message}'.strip(),
    }


def _protocol_status_snapshot(current_keys, force_refresh=False):
    signature = tuple((name, current_keys.get(name, '')) for name in sorted(current_keys))
    now = time.time()
    if (
        not force_refresh and
        key_status_cache['data'] is not None and
        key_status_cache['signature'] == signature and
        now - key_status_cache['timestamp'] < KEY_STATUS_CACHE_TTL
    ):
        return key_status_cache['data']

    data = {
        key_name: _protocol_status_for_key(key_name, key_value)
        for key_name, key_value in current_keys.items()
    }
    key_status_cache['timestamp'] = now
    key_status_cache['data'] = data
    key_status_cache['signature'] = signature
    return data


def _web_command_label(command):
    labels = {
        'install_fork': 'Установить из форка',
        'install_original': 'Установить оригинальную версию',
        'update': 'Обновить через форк',
        'remove': 'Удалить компоненты',
        'restart_services': 'Перезапустить сервисы',
        'dns_on': 'DNS Override ВКЛ',
        'dns_off': 'DNS Override ВЫКЛ',
        'reboot': 'Перезагрузить роутер',
    }
    return labels.get(command, command)


def _get_web_command_state():
    with web_command_lock:
        return dict(web_command_state)


def _set_web_flash_message(message):
    global web_flash_message
    with web_flash_lock:
        web_flash_message = message or ''


def _consume_web_flash_message():
    global web_flash_message
    with web_flash_lock:
        message = web_flash_message
        web_flash_message = ''
    return message


def _finish_web_command(command, result):
    with web_command_lock:
        web_command_state['running'] = False
        web_command_state['command'] = command
        web_command_state['label'] = _web_command_label(command)
        web_command_state['result'] = result
        web_command_state['finished_at'] = time.time()


def _execute_web_command(command):
    try:
        result = _run_web_command(command)
    except Exception as exc:
        result = f'Ошибка выполнения команды: {exc}'
    _finish_web_command(command, result)


def _start_web_command(command):
    label = _web_command_label(command)
    with web_command_lock:
        if web_command_state['running']:
            current_label = web_command_state['label'] or web_command_state['command']
            return False, f'⏳ Уже выполняется команда: {current_label}. Дождитесь завершения текущего запуска.'
        web_command_state['running'] = True
        web_command_state['command'] = command
        web_command_state['label'] = label
        web_command_state['result'] = ''
        web_command_state['started_at'] = time.time()
        web_command_state['finished_at'] = 0
    thread = threading.Thread(target=_execute_web_command, args=(command,), daemon=True)
    thread.start()
    return True, f'⏳ Команда "{label}" запущена. Страница обновится автоматически.'


def _load_bot_autostart():
    try:
        with open(BOT_AUTOSTART_FILE, 'r', encoding='utf-8') as file:
            return file.read().strip() == '1'
    except Exception:
        return False


def _invalidate_web_status_cache():
    web_status_cache['timestamp'] = 0
    web_status_cache['data'] = None


def _last_proxy_disable_reason():
    try:
        if not os.path.exists('/opt/etc/error.log'):
            return ''
        with open('/opt/etc/error.log', 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
        for line in reversed(lines[-80:]):
            marker = 'Прокси-режим '
            if marker not in line or ' отключён при старте: ' not in line:
                continue
            tail = line.split(' отключён при старте: ', 1)[1].strip()
            return tail
    except Exception:
        return ''
    return ''


def _load_proxy_mode():
    try:
        with open(PROXY_MODE_FILE, 'r', encoding='utf-8') as file:
            saved = file.read().strip()
        if saved in proxy_settings:
            return saved
    except Exception:
        pass
    return config.default_proxy_mode


def _wait_for_port(hosts, port, timeout=15):
    import socket
    if hosts is None:
        hosts = ['127.0.0.1', '::1', 'localhost']
    elif isinstance(hosts, str):
        hosts = [hosts]
    deadline = time.time() + timeout
    while time.time() < deadline:
        for host in hosts:
            try:
                addrs = socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
            except OSError:
                continue
            for family, socktype, proto, canonname, sockaddr in addrs:
                try:
                    with socket.socket(family, socktype, proto) as sock:
                        sock.settimeout(2)
                        sock.connect(sockaddr)
                        return True
                except OSError:
                    continue
        time.sleep(1)
    return False


def _port_is_listening(port):
    try:
        output = subprocess.check_output(['netstat', '-ltn'], stderr=subprocess.DEVNULL, text=True)
        for line in output.splitlines():
            if f':{port} ' in line or line.endswith(f':{port}'):
                return True
    except Exception:
        pass
    try:
        output = subprocess.check_output(['ss', '-ltn'], stderr=subprocess.DEVNULL, text=True)
        for line in output.splitlines():
            if f':{port} ' in line or line.endswith(f':{port}'):
                return True
    except Exception:
        pass
    return False

def _check_socks5_handshake(port, timeout=3):
    import socket
    try:
        with socket.create_connection(('127.0.0.1', int(port)), timeout=timeout) as sock:
            sock.sendall(b'\x05\x01\x00')
            data = sock.recv(2)
            return data == b'\x05\x00'
    except Exception:
        return False


def _wait_for_socks5_handshake(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _check_socks5_handshake(port):
            return True
        time.sleep(1)
    return False


def _ensure_service_port(port, restart_cmd=None, retries=2, sleep_after_restart=5, timeout=20):
    if _wait_for_port(None, port, timeout=timeout):
        return True
    if _port_is_listening(port):
        return True
    if restart_cmd:
        for _ in range(retries):
            os.system(restart_cmd)
            time.sleep(sleep_after_restart)
            if _wait_for_port(None, port, timeout=timeout):
                return True
            if _port_is_listening(port):
                return True
    return False


def _read_tail(file_path, lines=12):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.readlines()
        if not content:
            return ''
        return ''.join(content[-lines:]).strip()
    except Exception as exc:
        return f'Не удалось прочитать {file_path}: {exc}'


def _v2ray_diagnostics():
    config_path = CORE_PROXY_CONFIG_PATH
    error_path = CORE_PROXY_ERROR_LOG
    diagnostics = []
    if not os.path.exists(config_path):
        diagnostics.append(f'Конфигурация v2ray не найдена: {config_path}')
    else:
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
            inbounds = config_data.get('inbounds', [])
            ports = [str(inbound.get('port', '?')) for inbound in inbounds]
            details = [f'{port}({inbound.get("protocol", "?")})' for inbound, port in zip(inbounds, ports)]
            socks_status = []
            for inbound in inbounds:
                if inbound.get('protocol') == 'socks':
                    port = inbound.get('port')
                    if port:
                        socks_status.append(f'{port}:sock5={"ok" if _check_socks5_handshake(port) else "fail"}')
            if socks_status:
                details.append('socks:' + ','.join(socks_status))
            outbounds = []
            for outbound in config_data.get('outbounds', []):
                tag = outbound.get('tag', '')
                protocol = outbound.get('protocol', '')
                if protocol in ['vless', 'vmess']:
                    vnext = outbound.get('settings', {}).get('vnext', [])
                    if vnext:
                        entry = vnext[0]
                        addr = entry.get('address', '')
                        port = entry.get('port', '')
                        outbounds.append(f'{tag}:{protocol}->{addr}:{port}')
                    else:
                        outbounds.append(f'{tag}:{protocol}')
                else:
                    outbounds.append(f'{tag}:{protocol}')
            summary = f'Конфиг v2ray валиден. inbounds: {", ".join(ports)}'
            if details:
                summary += f' ({"; ".join(details)})'
            if outbounds:
                summary += f'; outbounds: {", ".join(outbounds)}'
            diagnostics.append(summary)
        except Exception as exc:
            diagnostics.append(f'Ошибка парсинга конфига v2ray: {exc}')
    error_tail = _read_tail(error_path, lines=12)
    if error_tail:
        diagnostics.append(f'Последние строки лога v2ray ({error_path}):\n{error_tail}')
    return ' '.join(diagnostics)


def _format_proxy_key_summary(key_type, key_value):
    if key_type == 'shadowsocks':
        server, port, method, password = _decode_shadowsocks_uri(key_value)
        return ('Параметры Shadowsocks: server={server}, port={port}, method={method}, '
                'password_len={password_len}').format(
                    server=server,
                    port=port,
                    method=method,
                    password_len=len(password))
    if key_type == 'vless':
        data = _parse_vless_key(key_value)
        return ('Параметры VLESS: address={address}, host={host}, port={port}, uuid={id}, network={type}, '
                'serviceName={serviceName}, sni={sni}, security={security}, flow={flow}').format(**data)
    if key_type == 'vmess':
        data = _parse_vmess_key(key_value)
        service_name = data.get('serviceName') or data.get('grpcSettings', {}).get('serviceName', '')
        return ('Параметры VMESS: host={add}, port={port}, id={id}, network={net}, tls={tls}, '
                'serviceName={service_name}').format(service_name=service_name, **data)
    if key_type == 'trojan':
        data = _parse_trojan_key(key_value)
        return ('Параметры Trojan: address={address}, port={port}, sni={sni}, security={security}, '
                'network={type}, password_len={password_len}').format(
                    address=data['address'],
                    port=data['port'],
                    sni=data['sni'],
                    security=data['security'],
                    type=data['type'],
                    password_len=len(data['password']))
    return ''


def _v2ray_outbound_summary(vmess_key=None, vless_key=None):
    try:
        config_data = _build_v2ray_config(vmess_key, vless_key)
        lines = []
        for outbound in config_data.get('outbounds', []):
            tag = outbound.get('tag', '')
            protocol = outbound.get('protocol', '')
            stream = outbound.get('streamSettings', {})
            if protocol in ['vless', 'vmess']:
                vnext = outbound.get('settings', {}).get('vnext', [])
                if vnext:
                    entry = vnext[0]
                    addr = entry.get('address', '')
                    port = entry.get('port', '')
                    lines.append(f'{tag}:{protocol} -> {addr}:{port} stream={stream}')
                else:
                    lines.append(f'{tag}:{protocol} stream={stream}')
            else:
                lines.append(f'{tag}:{protocol} stream={stream}')
        return ' '.join(lines)
    except Exception as exc:
        return f'Не удалось построить сводный outbound-конфиг: {exc}'


def _parse_trojan_key(key):
    parsed = urlparse(key)
    if parsed.scheme != 'trojan':
        raise ValueError('Неверный протокол, ожидается trojan://')
    if not parsed.hostname:
        raise ValueError('В trojan-ключе отсутствует адрес сервера')
    if not parsed.username:
        raise ValueError('В trojan-ключе отсутствует пароль')
    params = parse_qs(parsed.query)
    return {
        'address': parsed.hostname,
        'port': parsed.port or 443,
        'password': parsed.username,
        'sni': params.get('sni', [''])[0],
        'security': params.get('security', ['tls'])[0],
        'type': params.get('type', ['tcp'])[0],
        'host': params.get('host', [''])[0],
        'path': params.get('path', ['/'])[0] or '/',
        'serviceName': params.get('serviceName', [''])[0],
        'fingerprint': params.get('fp', params.get('fingerprint', ['chrome']))[0],
        'alpn': params.get('alpn', [''])[0],
    }


def _build_proxy_diagnostics(key_type, key_value):
    key_summary = _format_proxy_key_summary(key_type, key_value)
    if key_type not in ['vmess', 'vless']:
        return key_summary
    error_tail = _read_tail(CORE_PROXY_ERROR_LOG, lines=25)
    lines = [line.strip() for line in error_tail.splitlines() if line.strip()]
    last_issue = ''
    for line in reversed(lines):
        if ('failed to process outbound traffic' in line or
                'failed to find an available destination' in line or
                'dial tcp' in line or
                'lookup ' in line):
            last_issue = line
            break
    issue_summary = ''
    if last_issue:
        lookup_match = re.search(r'lookup\s+([^\s]+)', last_issue)
        dial_match = re.search(r'dial tcp\s+([^:]+:\d+)', last_issue)
        if 'server misbehaving' in last_issue and lookup_match:
            issue_summary = f'Причина: прокси-ядро не смогло разрешить адрес {lookup_match.group(1)} через локальный DNS.'
        elif 'operation was canceled' in last_issue and dial_match:
            issue_summary = f'Причина: сервер {dial_match.group(1)} не установил соединение через прокси-ядро.'
        elif 'connection refused' in last_issue and dial_match:
            issue_summary = f'Причина: сервер {dial_match.group(1)} отклонил соединение.'
        elif 'timed out' in last_issue or 'i/o timeout' in last_issue:
            issue_summary = 'Причина: соединение через прокси завершилось по таймауту.'
        elif 'failed to find an available destination' in last_issue:
            issue_summary = 'Причина: прокси-ядро не смогло построить рабочее исходящее соединение.'
    parts = []
    if issue_summary:
        parts.append(issue_summary)
    elif key_summary:
        parts.append(key_summary)
    return ' '.join(parts)


def _check_local_proxy_endpoint(key_type, port):
    if key_type in ['shadowsocks', 'vmess', 'vless', 'trojan']:
        if _wait_for_socks5_handshake(port, timeout=3):
            return True, f'Локальный SOCKS-порт 127.0.0.1:{port} отвечает как SOCKS5.'
        if _port_is_listening(port):
            return False, f'Локальный порт 127.0.0.1:{port} открыт, но не отвечает как SOCKS5.'
        return False, f'Локальный порт 127.0.0.1:{port} недоступен.'
    return True, ''


def _shadowsocks_runtime_mode():
    init_script = _read_text_file('/opt/etc/init.d/S22shadowsocks')
    if 'PROCS=ss-redir' in init_script or 'ss-redir' in init_script:
        return 'redir'
    if 'PROCS=ss-local' in init_script or 'ss-local' in init_script:
        return 'socks'
    return 'unknown'


def _apply_installed_proxy(key_type, key_value):
    settings = {
        'shadowsocks': {
            'label': 'Shadowsocks',
            'port': localportsh_bot,
            'restart_cmds': ['/opt/etc/init.d/S22shadowsocks restart', CORE_PROXY_SERVICE_SCRIPT + ' restart'],
            'startup_wait': 8,
        },
        'vmess': {
            'label': 'Vmess',
            'port': localportvmess,
            'restart_cmds': [CORE_PROXY_SERVICE_SCRIPT + ' restart'],
            'startup_wait': 18,
        },
        'vless': {
            'label': 'Vless',
            'port': localportvless,
            'restart_cmds': [CORE_PROXY_SERVICE_SCRIPT + ' restart'],
            'startup_wait': 18,
        },
        'trojan': {
            'label': 'Trojan',
            'port': localporttrojan_bot,
            'restart_cmds': ['/opt/etc/init.d/S22trojan restart', CORE_PROXY_SERVICE_SCRIPT + ' restart'],
            'startup_wait': 8,
        }
    }
    current = settings[key_type]
    active_mode = _load_proxy_mode()
    active_label = _proxy_mode_label(active_mode)
    for command in current['restart_cmds']:
        os.system(command)
    time.sleep(current['startup_wait'])

    diagnostics = _build_proxy_diagnostics(key_type, key_value)
    restart_cmd = current['restart_cmds'][-1]
    if not _ensure_service_port(current['port'], restart_cmd, retries=2, sleep_after_restart=5):
        return (f'⚠️ {current["label"]} ключ сохранён, но локальный порт 127.0.0.1:{current["port"]} '
                f'не поднялся. Текущий режим бота {active_label} сохранён. {diagnostics}').strip()

    endpoint_ok, endpoint_message = _check_local_proxy_endpoint(key_type, current['port'])
    if not endpoint_ok:
        return (f'⚠️ {current["label"]} ключ сохранён, но {endpoint_message} '
                f'Текущий режим бота {active_label} сохранён. {diagnostics}').strip()

    api_ok, api_probe_message = _check_telegram_api_through_proxy(
        proxy_settings.get(key_type),
        connect_timeout=10,
        read_timeout=15,
    )
    if api_ok:
        return (f'✅ {current["label"]} ключ сохранён. {endpoint_message} '
                f'Доступ к Telegram API через этот ключ подтверждён. '
                f'Текущий режим бота {active_label} сохранён.').strip()
    return (f'⚠️ {current["label"]} ключ сохранён. {endpoint_message} '
            f'Но Telegram API не проходит через этот ключ. '
            f'Текущий режим бота {active_label} сохранён. '
            f'❌ Не удалось подключиться к Telegram API: {api_probe_message} {diagnostics}').strip()


def update_proxy(proxy_type):
    global proxy_mode
    proxy_url = proxy_settings.get(proxy_type)
    if proxy_url and proxy_url.startswith('socks') and not _has_socks_support():
        return False, ('Для SOCKS-прокси требуется модуль PySocks. ' 
                       'Установите python3-pysocks или выберите другой режим.')

    proxy_mode = proxy_type
    if proxy_supports_http.get(proxy_type, False) and proxy_url:
        telebot.apihelper.proxy = {'https': proxy_url, 'http': proxy_url}
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        os.environ['http_proxy'] = proxy_url
    else:
        telebot.apihelper.proxy = {}
        for key in ['HTTPS_PROXY', 'HTTP_PROXY', 'https_proxy', 'http_proxy']:
            if key in os.environ:
                del os.environ[key]

    _save_proxy_mode(proxy_type)
    _invalidate_web_status_cache()
    _invalidate_key_status_cache()
    return True, None


def check_telegram_api(retries=2, retry_delay=7, connect_timeout=30, read_timeout=45):
    last_result = None
    for attempt in range(retries + 1):
        proxy_url = proxy_settings.get(proxy_mode)
        ok, probe_message = _check_telegram_api_through_proxy(proxy_url, connect_timeout=connect_timeout, read_timeout=read_timeout)
        if ok:
            return '✅ Доступ к api.telegram.org подтверждён.'
        if 'PySocks' in probe_message:
            return ('❌ Не удалось подключиться к Telegram API: отсутствует поддержка SOCKS (PySocks). '
                    'Установите python3-pysocks или используйте режим без SOCKS.')
        if proxy_mode == 'none':
            last_result = f'❌ Прямой доступ к api.telegram.org не проходит: {probe_message}'
        else:
            last_result = f'❌ Доступ к Telegram API через режим {proxy_mode} не проходит: {probe_message}'
            if attempt < retries:
                time.sleep(retry_delay)
    return last_result


def _web_status_snapshot(force_refresh=False):
    now = time.time()
    if (not force_refresh and web_status_cache['data'] is not None and
            now - web_status_cache['timestamp'] < WEB_STATUS_CACHE_TTL):
        return web_status_cache['data']
    state_label = 'polling активен' if bot_polling else ('ожидает запуска' if not bot_ready else 'процесс запущен, polling недоступен')
    socks_details = ''
    if proxy_mode in ['shadowsocks', 'vmess', 'vless', 'trojan']:
        port = {
            'shadowsocks': localportsh_bot,
            'vmess': localportvmess,
            'vless': localportvless,
            'trojan': localporttrojan_bot,
        }.get(proxy_mode)
        if port:
            socks_ok = _check_socks5_handshake(port)
            socks_details = f'Локальный SOCKS {proxy_mode} 127.0.0.1:{port}: {"доступен" if socks_ok else "не отвечает как SOCKS5"}'
    api_status = check_telegram_api(retries=1, retry_delay=1, connect_timeout=6, read_timeout=8)
    snapshot = {
        'state_label': state_label,
        'proxy_mode': proxy_mode,
        'api_status': api_status,
        'socks_details': socks_details,
        'fallback_reason': _last_proxy_disable_reason(),
    }
    web_status_cache['timestamp'] = now
    web_status_cache['data'] = snapshot
    return snapshot

# список смайлов для меню
#  ✅ ❌ ♻️ 📃 📆 🔑 📄 ❗ ️⚠️ ⚙️ 📝 📆 🗑 📄️⚠️ 🔰 ❔ ‼️ 📑
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.username not in usernames:
        bot.send_message(message.chat.id, 'Вы не являетесь автором канала')
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("🔰 Установка и удаление")
    item2 = types.KeyboardButton("🔑 Ключи и мосты")
    item3 = types.KeyboardButton("📝 Списки обхода")
    item4 = types.KeyboardButton("⚙️ Сервис")
    markup.add(item1, item2, item3, item4)
    bot.send_message(message.chat.id, '✅ Добро пожаловать в меню!', reply_markup=markup)

@bot.message_handler(content_types=['text'])
def bot_message(message):
    try:
        main = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m1 = types.KeyboardButton("🔰 Установка и удаление")
        m2 = types.KeyboardButton("🔑 Ключи и мосты")
        m3 = types.KeyboardButton("📝 Списки обхода")
        m4 = types.KeyboardButton("📄 Информация")
        m5 = types.KeyboardButton("⚙️ Сервис")
        main.add(m1, m2, m3)
        main.add(m4, m5)

        service = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m1 = types.KeyboardButton("♻️ Перезагрузить сервисы")
        m2 = types.KeyboardButton("‼️Перезагрузить роутер")
        m3 = types.KeyboardButton("‼️DNS Override")
        m4 = types.KeyboardButton("🔄 Обновления")
        back = types.KeyboardButton("🔙 Назад")
        service.add(m1, m2)
        service.add(m3, m4)
        service.add(back)

        if message.from_user.username not in usernames:
            bot.send_message(message.chat.id, 'Вы не являетесь автором канала')
            return
        if message.chat.type == 'private':
            global level, bypass

            if message.text == '⚙️ Сервис':
                bot.send_message(message.chat.id, '⚙️ Сервисное меню!', reply_markup=service)
                return

            if message.text == '♻️ Перезагрузить сервисы' or message.text == 'Перезагрузить сервисы':
                bot.send_message(message.chat.id, '🔄 Выполняется перезагрузка сервисов!', reply_markup=service)
                os.system('/opt/etc/init.d/S22shadowsocks restart')
                os.system('/opt/etc/init.d/S22trojan restart')
                os.system(CORE_PROXY_SERVICE_SCRIPT + ' restart')
                os.system('/opt/etc/init.d/S35tor restart')
                bot.send_message(message.chat.id, '✅ Сервисы перезагружены!', reply_markup=service)
                return

            if message.text == '‼️Перезагрузить роутер' or message.text == 'Перезагрузить роутер':
                os.system("ndmc -c system reboot")
                service_router_reboot = "🔄 Роутер перезагружается!\nЭто займет около 2 минут."
                bot.send_message(message.chat.id, service_router_reboot, reply_markup=service)
                return

            if message.text == '‼️DNS Override' or message.text == 'DNS Override':
                service = types.ReplyKeyboardMarkup(resize_keyboard=True)
                m1 = types.KeyboardButton("✅ DNS Override ВКЛ")
                m2 = types.KeyboardButton("❌ DNS Override ВЫКЛ")
                back = types.KeyboardButton("🔙 Назад")
                service.add(m1, m2)
                service.add(back)
                bot.send_message(message.chat.id, '‼️DNS Override!', reply_markup=service)
                return

            if message.text == "✅ DNS Override ВКЛ" or message.text == "❌ DNS Override ВЫКЛ":
                if message.text == "✅ DNS Override ВКЛ":
                    os.system("ndmc -c 'opkg dns-override'")
                    time.sleep(2)
                    os.system("ndmc -c 'system configuration save'")
                    bot.send_message(message.chat.id, '✅ DNS Override включен!\n🔄 Роутер перезагружается.',
                                     reply_markup=service)
                    time.sleep(5)
                    os.system("ndmc -c 'system reboot'")
                    return

                if message.text == "❌ DNS Override ВЫКЛ":
                    os.system("ndmc -c 'no opkg dns-override'")
                    time.sleep(2)
                    os.system("ndmc -c 'system configuration save'")
                    bot.send_message(message.chat.id, '✅ DNS Override выключен!\n🔄 Роутер перезагружается.',
                                     reply_markup=service)
                    time.sleep(5)
                    os.system("ndmc -c 'system reboot'")
                    return

                service_router_reboot = "🔄 Роутер перезагружается!\n⏳ Это займет около 2 минут."
                bot.send_message(message.chat.id, service_router_reboot, reply_markup=service)
                return

            if message.text == '📄 Информация':
                url = _raw_github_url('info.md')
                info_bot = requests.get(url).text
                bot.send_message(message.chat.id, info_bot, parse_mode='Markdown', disable_web_page_preview=True,
                                 reply_markup=main)
                return

            if message.text == '/keys_free':
                url = _raw_github_url('keys.md')
                keys_free = requests.get(url).text
                bot.send_message(message.chat.id, keys_free, parse_mode='Markdown', disable_web_page_preview=True)
                return

            if message.text == '🔄 Обновления' or message.text == '/check_update':
                url = _raw_github_url('version.md')
                bot_new_version = requests.get(url).text

                with open(BOT_SOURCE_PATH, encoding='utf-8') as file:
                    for line in file.readlines():
                        if line.startswith('# ВЕРСИЯ СКРИПТА'):
                            s = line.replace('# ', '')
                            bot_version = s.strip()

                service_bot_version = "*ВАША ТЕКУЩАЯ " + str(bot_version) + "*\n\n"
                service_new_version = "*ПОСЛЕДНЯЯ ДОСТУПНАЯ ВЕРСИЯ:*\n\n" + str(bot_new_version)
                service_update_info = service_bot_version + service_new_version
                # bot.send_message(message.chat.id, service_bot_version, parse_mode='Markdown', reply_markup=service)
                bot.send_message(message.chat.id, service_update_info, parse_mode='Markdown', reply_markup=service)

                service_update_msg = "Если вы хотите обновить текущую версию на более новую, нажмите сюда /update"
                bot.send_message(message.chat.id, service_update_msg, parse_mode='Markdown', reply_markup=service)
                return

            if message.text == '/update':
                bot.send_message(message.chat.id, 'Устанавливаются обновления, подождите!', reply_markup=service)
                return_code, output = _run_script_action('-update', fork_repo_owner, fork_repo_name)
                _send_telegram_chunks(message.chat.id, output, reply_markup=service)
                if return_code == 0:
                    bot.send_message(message.chat.id, '✅ Обновление завершено.', reply_markup=service)
                else:
                    bot.send_message(message.chat.id, '⚠️ Обновление завершилось с ошибкой. Полный лог отправлен выше.', reply_markup=service)
                return

            if message.text == '🔙 Назад' or message.text == "Назад":
                bot.send_message(message.chat.id, '✅ Добро пожаловать в меню!', reply_markup=main)
                level = 0
                bypass = -1
                return

            if level == 1:
                # значит это список обхода блокировок
                dirname = '/opt/etc/unblock/'
                dirfiles = os.listdir(dirname)

                for fln in dirfiles:
                    if fln == message.text + '.txt':
                        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                        item1 = types.KeyboardButton("📑 Показать список")
                        item2 = types.KeyboardButton("📝 Добавить в список")
                        item3 = types.KeyboardButton("🗑 Удалить из списка")
                        back = types.KeyboardButton("🔙 Назад")
                        markup.row(item1, item2, item3)
                        markup.row(back)
                        level = 2
                        bypass = message.text
                        bot.send_message(message.chat.id, "Меню " + bypass, reply_markup=markup)
                        return

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                back = types.KeyboardButton("🔙 Назад")
                markup.add(back)
                bot.send_message(message.chat.id, "Не найден", reply_markup=markup)
                return

            if level == 2 and message.text == "📑 Показать список":
                file = open('/opt/etc/unblock/' + bypass + '.txt')
                flag = True
                s = ''
                sites = []
                for line in file:
                    sites.append(line)
                    flag = False
                if flag:
                    s = 'Список пуст'
                file.close()
                sites.sort()
                if not flag:
                    for line in sites:
                        s = str(s) + '\n' + line.replace("\n", "")
                if len(s) > 4096:
                    for x in range(0, len(s), 4096):
                        bot.send_message(message.chat.id, s[x:x + 4096])
                else:
                    bot.send_message(message.chat.id, s)
                #bot.send_message(message.chat.id, s)
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("📑 Показать список")
                item2 = types.KeyboardButton("📝 Добавить в список")
                item3 = types.KeyboardButton("🗑 Удалить из списка")
                back = types.KeyboardButton("🔙 Назад")
                markup.row(item1, item2, item3)
                markup.row(back)
                bot.send_message(message.chat.id, "Меню " + bypass, reply_markup=markup)
                return

            if level == 2 and message.text == "📝 Добавить в список":
                bot.send_message(message.chat.id,
                                 "Введите имя сайта или домена для разблокировки, "
                                 "либо воспользуйтесь меню для других действий")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("Добавить обход блокировок соцсетей")
                back = types.KeyboardButton("🔙 Назад")
                markup.add(item1, back)
                level = 3
                bot.send_message(message.chat.id, "Меню " + bypass, reply_markup=markup)
                return

            if level == 2 and message.text == "🗑 Удалить из списка":
                bot.send_message(message.chat.id,
                                 "Введите имя сайта или домена для удаления из листа разблокировки,"
                                 "либо возвратитесь в главное меню")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                back = types.KeyboardButton("🔙 Назад")
                markup.add(back)
                level = 4
                bot.send_message(message.chat.id, "Меню " + bypass, reply_markup=markup)
                return

            if level == 3:
                f = open('/opt/etc/unblock/' + bypass + '.txt')
                mylist = set()
                for line in f:
                    mylist.add(line.replace('\n', ''))
                f.close()
                k = len(mylist)
                if message.text == "Добавить обход блокировок соцсетей":
                    url = "https://raw.githubusercontent.com/tas-unn/bypass_keenetic/main/socialnet.txt"
                    s = requests.get(url).text
                    lst = s.split('\n')
                    for line in lst:
                        if len(line) > 1:
                            mylist.add(line.replace('\n', ''))
                else:
                    if len(message.text) > 1:
                        mas = message.text.split('\n')
                        for site in mas:
                            mylist.add(site)
                sortlist = []
                for line in mylist:
                    sortlist.append(line)
                sortlist.sort()
                f = open('/opt/etc/unblock/' + bypass + '.txt', 'w')
                for line in sortlist:
                    f.write(line + '\n')
                f.close()
                if k != len(sortlist):
                    bot.send_message(message.chat.id, "✅ Успешно добавлено")
                else:
                    bot.send_message(message.chat.id, "Было добавлено ранее")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("📑 Показать список")
                item2 = types.KeyboardButton("📝 Добавить в список")
                item3 = types.KeyboardButton("🗑 Удалить из списка")
                back = types.KeyboardButton("🔙 Назад")
                markup.row(item1, item2, item3)
                markup.row(back)
                subprocess.call(["/opt/bin/unblock_update.sh"])
                level = 2
                bot.send_message(message.chat.id, "Меню " + bypass, reply_markup=markup)
                return

            if level == 4:
                f = open('/opt/etc/unblock/' + bypass + '.txt')
                mylist = set()
                for line in f:
                    mylist.add(line.replace('\n', ''))
                f.close()
                k = len(mylist)
                mas = message.text.split('\n')
                for site in mas:
                    mylist.discard(site)
                f = open('/opt/etc/unblock/' + bypass + '.txt', 'w')
                for line in mylist:
                    f.write(line + '\n')
                f.close()
                if k != len(mylist):
                    bot.send_message(message.chat.id, "✅ Успешно удалено")
                else:
                    bot.send_message(message.chat.id, "Не найдено в списке")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("📑 Показать список")
                item2 = types.KeyboardButton("📝 Добавить в список")
                item3 = types.KeyboardButton("🗑 Удалить из списка")
                back = types.KeyboardButton("🔙 Назад")
                markup.row(item1, item2, item3)
                markup.row(back)
                level = 2
                subprocess.call(["/opt/bin/unblock_update.sh"])
                bot.send_message(message.chat.id, "Меню " + bypass, reply_markup=markup)
                return

            if level == 5:
                level = 0
                _install_proxy_from_message(message, 'shadowsocks', message.text, main)
                return

            if level == 6:
                tormanually(message.text)
                os.system('/opt/etc/init.d/S35tor restart')
                level = 0
                bot.send_message(message.chat.id, '✅ Успешно обновлено', reply_markup=main)
                # return

            if level == 8:
                # значит это ключи и мосты
                if message.text == 'Где брать ключи❔':
                    url = _raw_github_url('keys.md')
                    keys = requests.get(url).text
                    bot.send_message(message.chat.id, keys, parse_mode='Markdown', disable_web_page_preview=True)
                    level = 8

                if message.text == 'Tor':
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    item1 = types.KeyboardButton("Tor вручную")
                    item2 = types.KeyboardButton("Tor через telegram")
                    markup.add(item1, item2)
                    back = types.KeyboardButton("🔙 Назад")
                    markup.add(back)
                    bot.send_message(message.chat.id, '✅ Добро пожаловать в меню Tor!', reply_markup=markup)

                if message.text == 'Shadowsocks':
                    #bot.send_message(message.chat.id, "Скопируйте ключ сюда")
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    back = types.KeyboardButton("🔙 Назад")
                    markup.add(back)
                    level = 5
                    bot.send_message(message.chat.id, "🔑 Скопируйте ключ сюда", reply_markup=markup)
                    return

                if message.text == 'Vmess':
                    #bot.send_message(message.chat.id, "Скопируйте ключ сюда")
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    back = types.KeyboardButton("🔙 Назад")
                    markup.add(back)
                    level = 9
                    bot.send_message(message.chat.id, "🔑 Скопируйте ключ сюда", reply_markup=markup)
                    return

                if message.text == 'Vless':
                    #bot.send_message(message.chat.id, "Скопируйте ключ сюда")
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    back = types.KeyboardButton("🔙 Назад")
                    markup.add(back)
                    level = 11
                    bot.send_message(message.chat.id, "🔑 Скопируйте ключ сюда", reply_markup=markup)
                    return

                if message.text == 'Trojan':
                    #bot.send_message(message.chat.id, "Скопируйте ключ сюда")
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    back = types.KeyboardButton("🔙 Назад")
                    markup.add(back)
                    level = 10
                    bot.send_message(message.chat.id, "🔑 Скопируйте ключ сюда", reply_markup=markup)
                    return

            if level == 9:
                level = 0
                _install_proxy_from_message(message, 'vmess', message.text, main)
                return

            if level == 10:
                level = 0
                _install_proxy_from_message(message, 'trojan', message.text, main)
                return

            if level == 11:
                level = 0
                _install_proxy_from_message(message, 'vless', message.text, main)
                return

            if message.text == 'Tor вручную':
                #bot.send_message(message.chat.id, "Скопируйте ключ сюда")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                back = types.KeyboardButton("🔙 Назад")
                markup.add(back)
                level = 6
                bot.send_message(message.chat.id, "🔑 Скопируйте ключ сюда", reply_markup=markup)
                return

            if message.text == '🌐 Через браузер':
                bot.send_message(message.chat.id,
                                 f'Откройте в браузере: http://{routerip}:{browser_port}/\n'
                                 'Введите ключ Shadowsocks, Vmess, Vless или Trojan на странице.', reply_markup=main)
                return

            if message.text == 'Tor через telegram':
                tor()
                os.system('/opt/etc/init.d/S35tor restart')
                level = 0
                bot.send_message(message.chat.id, '✅ Успешно обновлено', reply_markup=main)
                return

            if message.text == '🔰 Установка и удаление':
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("♻️ Установка & переустановка")
                item2 = types.KeyboardButton("⚠️ Удаление")
                back = types.KeyboardButton("🔙 Назад")
                markup.row(item1, item2)
                markup.row(back)
                bot.send_message(message.chat.id, '🔰 Установка и удаление', reply_markup=markup)
                return

            if message.text == '♻️ Установка & переустановка':
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("Оригинальная версия")
                item2 = types.KeyboardButton(fork_button_label)
                back = types.KeyboardButton("🔙 Назад")
                markup.row(item1, item2)
                markup.row(back)
                bot.send_message(message.chat.id, 'Выберите репозиторий', reply_markup=markup)
                return

            if message.text == "Оригинальная версия" or message.text == fork_button_label:
                if message.text == "Оригинальная версия":
                    repo = "tas-unn"
                    repo_name = 'bypass_keenetic'
                else:
                    repo = fork_repo_owner
                    repo_name = fork_repo_name

                return_code, output = _run_script_action('-install', repo, repo_name)
                _send_telegram_chunks(message.chat.id, output, reply_markup=main)

                if return_code != 0:
                    bot.send_message(message.chat.id,
                                     '⚠️ Установка завершилась с ошибкой. Полный лог отправлен выше.',
                                     reply_markup=main)
                    return

                bot.send_message(message.chat.id,
                                 "Установка завершена. Теперь нужно немного настроить роутер и перейти к "
                                 "спискам для разблокировок. "
                                 "Ключи для Vmess, Shadowsocks и Trojan необходимо установить вручную, "
                                 "ключи для Tor можно установить автоматически: " 
                                 "Ключи и Мосты -> Tor -> Tor через telegram.",
                                 reply_markup=main)

                bot.send_message(message.chat.id,
                                 "Что бы завершить настройку роутера, Зайдите в меню сервис -> DNS Override -> ВКЛ. "
                                 "Учтите, после выполнения команды, роутер перезагрузится, это займет около 2 минут.",
                                 reply_markup=main)

                subprocess.call(["/opt/bin/unblock_update.sh"])
                # os.system('/opt/bin/unblock_update.sh')
                return

            if message.text == '⚠️ Удаление':
                return_code, output = _run_script_action('-remove', fork_repo_owner, fork_repo_name)
                _send_telegram_chunks(message.chat.id, output, reply_markup=service)
                if return_code == 0:
                    bot.send_message(message.chat.id, '✅ Удаление завершено.', reply_markup=service)
                else:
                    bot.send_message(message.chat.id, '⚠️ Удаление завершилось с ошибкой. Полный лог отправлен выше.', reply_markup=service)
                return

            if message.text == "📝 Списки обхода":
                level = 1
                dirname = '/opt/etc/unblock/'
                dirfiles = os.listdir(dirname)
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markuplist = []
                for fln in dirfiles:
                    # markup.add(fln.replace(".txt", ""))
                    btn = fln.replace(".txt", "")
                    markuplist.append(btn)
                markup.add(*markuplist)
                back = types.KeyboardButton("🔙 Назад")
                markup.add(back)
                bot.send_message(message.chat.id, "📝 Списки обхода", reply_markup=markup)
                return

            if message.text == "🔑 Ключи и мосты":
                level = 8
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("Shadowsocks")
                item2 = types.KeyboardButton("Vmess")
                item3 = types.KeyboardButton("Vless")
                item4 = types.KeyboardButton("Trojan")
                item5 = types.KeyboardButton("Где брать ключи❔")
                item6 = types.KeyboardButton("🌐 Через браузер")
                markup.add(item1, item2)
                markup.add(item3, item4)
                markup.add(item5)
                markup.add(item6)
                back = types.KeyboardButton("🔙 Назад")
                markup.add(back)
                bot.send_message(message.chat.id, "🔑 Ключи и мосты", reply_markup=markup)
                return

    except Exception as error:
        file = open("/opt/etc/error.log", "w")
        file.write(str(error))
        file.close()
        os.chmod(r"/opt/etc/error.log", 0o0755)

class KeyInstallHTTPRequestHandler(BaseHTTPRequestHandler):
    def _send_html(self, html, status=200):
        body = html.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _send_redirect(self, location='/'):
        self.send_response(303)
        self.send_header('Location', location)
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True

    def _build_form(self, message=''):
        status = _web_status_snapshot(force_refresh=True)
        command_state = _get_web_command_state()
        current_keys = _load_current_keys()
        protocol_statuses = _protocol_status_snapshot(current_keys)
        unblock_lists = _load_unblock_lists()

        message_block = ''
        if message:
            safe_message = html.escape(message)
            message_block = f'''<div class="notice notice-result">
  <strong>Результат</strong>
  <pre class="log-output">{safe_message}</pre>
</div>'''

        command_block = ''
        if command_state['label']:
            command_title = 'Команда выполняется' if command_state['running'] else 'Последняя команда'
            command_text = command_state['result'] or f'⏳ {command_state["label"]} ещё выполняется. Обновление страницы происходит автоматически.'
            command_block = f'''<div class="notice notice-status">
  <strong>{html.escape(command_title)}: {html.escape(command_state['label'])}</strong>
  <pre class="log-output">{html.escape(command_text)}</pre>
</div>'''

        socks_block = ''
        if status['socks_details']:
            socks_block = f'<p class="status-note">{html.escape(status["socks_details"])}' + '</p>'

        fallback_block = ''
        if status.get('fallback_reason') and status['proxy_mode'] == 'none':
            fallback_block = f'<p class="status-note">Последняя неудачная попытка прокси: {html.escape(status["fallback_reason"])}</p>'

        current_mode_label = {
            'none': 'Без VPN',
            'shadowsocks': 'Shadowsocks',
            'vmess': 'Vmess',
            'vless': 'Vless',
            'trojan': 'Trojan',
        }.get(status['proxy_mode'], status['proxy_mode'])
        list_route_label = _transparent_list_route_label()

        status_block = f'''<div class="notice notice-status hero-status hero-status-compact">
    <div class="hero-status-header">
        <strong>Связь с Telegram API</strong>
        <div class="traffic-inline">
            <span class="traffic-chip"><span class="traffic-chip-label">Бот</span><span class="traffic-chip-value">{html.escape(current_mode_label)}</span></span>
            <span class="traffic-chip"><span class="traffic-chip-label">Списки</span><span class="traffic-chip-value">{html.escape(list_route_label)}</span></span>
        </div>
    </div>
    <p>{html.escape(status['api_status'])}</p>
    {socks_block}
    {fallback_block}
</div>'''

        mode_picker_block = f'''<div id="mode-picker" class="hero-popover mode-picker hidden">
    <form method="post" action="/set_proxy" class="mode-picker-form">
        <label class="mode-picker-label" for="hero-proxy-type">Активный протокол</label>
        <select id="hero-proxy-type" name="proxy_type">
            <option value="none"{' selected' if proxy_mode == 'none' else ''}>Без VPN (по умолчанию)</option>
            <option value="shadowsocks"{' selected' if proxy_mode == 'shadowsocks' else ''}>Shadowsocks</option>
            <option value="vmess"{' selected' if proxy_mode == 'vmess' else ''}>Vmess</option>
            <option value="vless"{' selected' if proxy_mode == 'vless' else ''}>Vless</option>
            <option value="trojan"{' selected' if proxy_mode == 'trojan' else ''}>Trojan</option>
        </select>
        <button type="submit">Применить режим</button>
    </form>
</div>'''

        protocol_sections = [
            ('vless', 'Vless', 6, 'vless://...'),
            ('vmess', 'Vmess', 6, 'vmess://...'),
            ('trojan', 'Trojan', 5, 'trojan://...'),
            ('shadowsocks', 'Shadowsocks', 5, 'shadowsocks://...'),
        ]
        protocol_cards = []
        for key_name, title, rows, placeholder in protocol_sections:
            safe_value = html.escape(current_keys.get(key_name, ''))
            safe_title = html.escape(title)
            status_info = protocol_statuses.get(key_name, {'tone': 'empty', 'label': 'Не сохранён', 'details': 'Ключ ещё не сохранён на роутере.'})
            protocol_cards.append(f'''<section class="panel protocol-card">
        <div class="card-topline">
            <span class="eyebrow">Ключ подключения</span>
            <span class="key-status-badge key-status-{status_info['tone']}">{html.escape(status_info['label'])}</span>
        </div>
        <h2>{safe_title}</h2>
        <p class="key-status-note">{html.escape(status_info['details'])}</p>
    <form method="post" action="/install">
      <input type="hidden" name="type" value="{key_name}">
      <textarea name="key" rows="{rows}" placeholder="{html.escape(placeholder)}" required>{safe_value}</textarea>
      <button type="submit">Сохранить {safe_title}</button>
    </form>
  </section>''')
        protocol_cards_html = ''.join(protocol_cards)

        command_buttons = [
            ('install_fork', 'Установить из форка', ''),
            ('update', 'Обновить через форк', ''),
            ('restart_services', 'Перезапустить сервисы', ''),
            ('dns_on', 'DNS Override ВКЛ', ''),
            ('dns_off', 'DNS Override ВЫКЛ', ''),
            ('remove', 'Удалить компоненты', 'danger'),
            ('reboot', 'Перезагрузить роутер', 'danger'),
        ]
        command_buttons_html = ''.join(
            f'''<form method="post" action="/command">
            <input type="hidden" name="command" value="{command}">
            <button type="submit" class="{button_class}">{html.escape(label)}</button>
        </form>'''
            for command, label, button_class in command_buttons
        )

        unblock_cards = []
        for entry in unblock_lists:
            safe_name = html.escape(entry['name'])
            safe_label = html.escape(entry['label'])
            safe_content = html.escape(entry['content'])
            unblock_cards.append(f'''<section class="panel unblock-card">
        <div class="card-topline">
            <span class="eyebrow">Список обхода</span>
            <span class="file-chip">{safe_name}</span>
        </div>
    <h2>{safe_label}</h2>
    <form method="post" action="/save_unblock_list">
      <input type="hidden" name="list_name" value="{safe_name}">
      <textarea name="content" rows="8" placeholder="example.org&#10;api.telegram.org">{safe_content}</textarea>
      <button type="submit">Сохранить список</button>
    </form>
  </section>''')
        unblock_lists_block = ''.join(unblock_cards)

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    {'<meta http-equiv="refresh" content="4">' if command_state['running'] else ''}
  <title>Установка ключей VPN</title>
    <style>
        :root{{
            --bg:#12161d;
            --bg-accent:#1a2330;
            --surface:#171e28;
            --surface-soft:#202a38;
            --surface-strong:#263243;
            --border:#334155;
            --text:#edf3ff;
            --muted:#9fb0c8;
            --primary:#4f8cff;
            --primary-hover:#6aa0ff;
            --secondary:#d78644;
            --danger:#c95a47;
            --success-bg:#163326;
            --success-border:#2d7650;
            --warn-bg:#3e2e16;
            --warn-border:#b78332;
            --shadow:0 18px 40px rgba(2, 6, 23, 0.34);
        }}
        [data-theme="light"]{{
            --bg:#f3efe6;
            --bg-accent:#e7dcc7;
            --surface:#fffdf8;
            --surface-soft:#f5ede0;
            --surface-strong:#efe2cb;
            --border:#d7c5aa;
            --text:#1f2933;
            --muted:#6f7a86;
            --primary:#1f7a6a;
            --primary-hover:#165f53;
            --secondary:#c96f32;
            --danger:#a8442f;
            --success-bg:#e5f4ea;
            --success-border:#8cb79a;
            --warn-bg:#fff0d9;
            --warn-border:#d6a35b;
            --shadow:0 18px 40px rgba(76, 58, 36, 0.12);
        }}
        *{{box-sizing:border-box;}}
        body{{
            margin:0;
                        font-family:Segoe UI,Helvetica,Arial,sans-serif;
            color:var(--text);
                        background:
                radial-gradient(circle at top left, rgba(215,134,68,.16), transparent 34%),
                radial-gradient(circle at top right, rgba(79,140,255,.16), transparent 28%),
                linear-gradient(180deg, #0f141c 0%, var(--bg) 100%);
                        padding:20px;
        }}
        [data-theme="light"] body{{
            background:
                radial-gradient(circle at top left, rgba(201,111,50,.18), transparent 34%),
                radial-gradient(circle at top right, rgba(31,122,106,.16), transparent 28%),
                linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
        }}
                .shell{{max-width:1180px;margin:0 auto;}}
        .hero{{margin-bottom:16px;padding:22px 24px;border:1px solid var(--border);border-radius:24px;background:linear-gradient(140deg, rgba(23,30,40,.98), rgba(32,42,56,.9));box-shadow:var(--shadow);}}
        [data-theme="light"] .hero{{background:linear-gradient(140deg, rgba(255,253,248,.98), rgba(239,226,203,.88));}}
                .hero-copy{{max-width:700px;}}
                .hero-row{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;}}
                .hero-actions{{display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap;position:relative;justify-content:flex-end;}}
        .hero-meta{{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 0;}}
        .hero-chip{{display:inline-flex;align-items:center;padding:8px 12px;border-radius:999px;background:rgba(79,140,255,.08);border:1px solid rgba(96,165,250,.18);font-size:13px;font-weight:700;color:var(--text);}}
        .theme-toggle{{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:999px;border:1px solid var(--border);background:rgba(255,255,255,.03);color:var(--text);font-size:13px;font-weight:700;cursor:pointer;box-shadow:none;white-space:nowrap;}}
                .mode-toggle{{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:999px;border:1px solid var(--border);background:rgba(255,255,255,.03);color:var(--text);font-size:13px;font-weight:700;cursor:pointer;box-shadow:none;white-space:nowrap;}}
        .theme-toggle:hover{{filter:none;transform:none;background:rgba(255,255,255,.06);}}
                .mode-toggle:hover{{filter:none;transform:none;background:rgba(255,255,255,.06);}}
                .hero-popover{{position:absolute;top:54px;right:0;min-width:260px;padding:14px;border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg, rgba(23,30,40,.98), rgba(32,42,56,.96));box-shadow:var(--shadow);z-index:10;}}
                [data-theme="light"] .hero-popover{{background:linear-gradient(180deg, rgba(255,253,248,.98), rgba(245,237,224,.96));}}
                .hidden{{display:none;}}
                .mode-picker-form{{display:grid;gap:10px;}}
                .mode-picker-label{{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);}}
        h1{{margin:0 0 8px;font-size:clamp(30px,5vw,48px);line-height:1.02;letter-spacing:-0.04em;color:var(--text);}}
        h2{{margin:0 0 14px;font-size:20px;color:var(--text);}}
            p{{margin:0 0 8px;line-height:1.5;color:var(--muted);}}
        .hero strong{{color:var(--text);}}
                .layout{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}}
        .panel{{padding:18px;border:1px solid var(--border);border-radius:22px;background:linear-gradient(180deg, rgba(23,30,40,.96), rgba(32,42,56,.94));box-shadow:var(--shadow);}}
        [data-theme="light"] .panel{{background:linear-gradient(180deg, rgba(255,253,248,.96), rgba(245,237,224,.94));}}
        form{{display:grid;gap:12px;}}
                input,textarea,select{{width:100%;padding:13px 14px;border-radius:14px;border:1px solid var(--border);background:var(--surface-soft);color:var(--text);font-size:16px;outline:none;}}
                input:focus,textarea:focus,select:focus{{border-color:rgba(31,122,106,.6);box-shadow:0 0 0 4px rgba(31,122,106,.08);}}
        textarea{{min-height:138px;resize:vertical;}}
                input::placeholder,textarea::placeholder{{color:#8b8f92;}}
                button{{padding:13px 16px;border:none;border-radius:14px;background:linear-gradient(135deg, var(--primary), #246f61);color:#fff;font-size:15px;font-weight:700;cursor:pointer;transition:transform .15s ease, filter .15s ease, box-shadow .15s ease;box-shadow:0 10px 20px rgba(31,122,106,.18);}}
        button:hover{{filter:brightness(1.08);transform:translateY(-1px);}}
                button.danger{{background:linear-gradient(135deg, var(--danger), #85311f);box-shadow:0 10px 20px rgba(168,68,47,.18);}}
                .secondary-button{{background:linear-gradient(135deg, var(--secondary), #b85b27);box-shadow:0 10px 20px rgba(201,111,50,.18);}}
        .status-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:14px;}}
                .status-card{{padding:14px;border-radius:18px;background:rgba(79,140,255,.08);border:1px solid rgba(96,165,250,.18);}}
                .status-label{{display:block;margin-bottom:8px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#90a5c4;}}
                .status-value{{font-size:16px;color:var(--text);}}
                .notice{{padding:12px 14px;border-radius:16px;margin-bottom:14px;}}
                .notice strong{{display:block;margin-bottom:8px;color:var(--text);}}
        .notice-result{{background:var(--warn-bg);border:1px solid var(--warn-border);}}
        .notice-status{{background:var(--success-bg);border:1px solid var(--success-border);}}
            .hero-status{{margin-top:12px;margin-bottom:0;}}
            .hero-status-compact p:last-child{{margin-bottom:0;}}
            .hero-status-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:6px;}}
            .traffic-inline{{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end;}}
            .traffic-chip{{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);}}
            .traffic-chip-label{{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}}
            .traffic-chip-value{{font-size:13px;font-weight:700;color:var(--text);}}
                .status-note{{margin-top:6px;color:var(--text);font-size:14px;line-height:1.4;}}
                .log-output{{margin:0;white-space:pre-wrap;word-break:break-word;font:13px/1.45 Consolas,Monaco,monospace;color:var(--text);}}
                .eyebrow{{display:inline-block;margin-bottom:10px;font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#8b6f4a;}}
                .section-title{{margin:0 0 6px;font-size:24px;color:var(--text);}}
                .section-subtitle{{margin:0;color:var(--muted);}}
                .start-card{{display:flex;flex-direction:column;justify-content:space-between;}}
                .command-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px;}}
                .card-topline{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;}}
                .file-chip{{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:rgba(201,111,50,.12);border:1px solid rgba(201,111,50,.2);font-size:12px;font-weight:700;color:#7c4b21;}}
                .key-status-badge{{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;border:1px solid transparent;font-size:12px;font-weight:700;white-space:nowrap;}}
                .key-status-ok{{background:rgba(31,122,106,.14);border-color:rgba(31,122,106,.3);color:#9be4d3;}}
                .key-status-fail{{background:rgba(168,68,47,.14);border-color:rgba(168,68,47,.28);color:#ffbeb2;}}
                .key-status-warn{{background:rgba(201,111,50,.14);border-color:rgba(201,111,50,.28);color:#f6c892;}}
                .key-status-empty{{background:rgba(159,176,200,.1);border-color:rgba(159,176,200,.18);color:var(--muted);}}
                .key-status-note{{margin:-4px 0 4px;color:var(--muted);font-size:14px;line-height:1.45;}}
        .wide{{grid-column:1 / -1;}}
        @media (max-width: 760px){{
            body{{padding:12px;}}
                        .hero{{padding:16px;border-radius:20px;}}
            .hero-row{{flex-direction:column;align-items:stretch;}}
            .hero-actions{{width:100%;justify-content:stretch;}}
            .hero-status-header{{flex-direction:column;align-items:flex-start;}}
            .traffic-inline{{justify-content:flex-start;}}
            .theme-toggle,.mode-toggle{{justify-content:center;}}
            .hero-popover{{position:static;min-width:0;width:100%;}}
            .layout{{grid-template-columns:1fr;gap:12px;}}
                        .command-grid{{grid-template-columns:1fr;}}
            .status-grid{{grid-template-columns:1fr;}}
                        .panel{{padding:16px;border-radius:18px;}}
            button,input,textarea,select{{font-size:16px;}}
        }}
    </style>
    <script>
        (function() {{
            const savedTheme = localStorage.getItem('router-theme');
            const theme = savedTheme === 'light' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', theme);
        }})();

        function toggleTheme() {{
            const root = document.documentElement;
            const nextTheme = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            root.setAttribute('data-theme', nextTheme);
            localStorage.setItem('router-theme', nextTheme);
            const label = document.getElementById('theme-toggle-label');
            if (label) {{
                label.textContent = nextTheme === 'light' ? 'Светлая тема' : 'Темная тема';
            }}
        }}

        function toggleModePicker() {{
            const picker = document.getElementById('mode-picker');
            if (!picker) {{
                return;
            }}
            picker.classList.toggle('hidden');
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const label = document.getElementById('theme-toggle-label');
            if (label) {{
                label.textContent = currentTheme === 'light' ? 'Светлая тема' : 'Темная тема';
            }}
            document.addEventListener('click', function(event) {{
                const picker = document.getElementById('mode-picker');
                const toggle = document.getElementById('mode-toggle-button');
                if (!picker || !toggle) {{
                    return;
                }}
                if (picker.classList.contains('hidden')) {{
                    return;
                }}
                if (!picker.contains(event.target) && !toggle.contains(event.target)) {{
                    picker.classList.add('hidden');
                }}
            }});
        }});
    </script>
</head>
<body>
    <div class="shell">
    <div class="hero">
        <div class="hero-row">
                <div class="hero-copy">
                        <h1>Установка ключей VPN</h1>
                        <p>Страница показывает не только состояние процесса, но и реальный статус связи с Telegram API.</p>
                        <p><strong>Вставляйте ключ полной строкой, как в Telegram.</strong></p>
                </div>
        <div class="hero-actions">
            <button type="button" id="mode-toggle-button" class="mode-toggle" onclick="toggleModePicker()">
                <span>Режим</span>
                <span>{html.escape(current_mode_label)}</span>
            </button>
            <button type="button" class="theme-toggle" onclick="toggleTheme()">
                <span>Тема</span>
                <span id="theme-toggle-label">Темная тема</span>
            </button>
            {mode_picker_block}
        </div>
        </div>
                {status_block}
    </div>
    {message_block}
    {command_block}
        <section class="panel start-card">
            <div>
                <span class="eyebrow">Запуск</span>
                <h2 class="section-title">Быстрый старт</h2>
                    <p class="section-subtitle">После установки ключей можно сразу запустить бота.</p>
            </div>
            <form method="post" action="/start">
                <button type="submit">Запустить бота</button>
            </form>
        </section>
        <div class="layout">
        <section class="panel wide">
            <span class="eyebrow">Ключи и мосты</span>
            <h2 class="section-title">Подключения по протоколам</h2>
            <p class="section-subtitle">Храните рабочий ключ в нужной карточке. Текущий режим выбирается отдельно выше.</p>
        </section>
        {protocol_cards_html}
        <section class="panel wide">
                <span class="eyebrow">Сервис роутера</span>
                <h2 class="section-title">Команды установки и обслуживания</h2>
                <p class="section-subtitle">Обычные действия и потенциально опасные команды разделены по цвету, чтобы ими было труднее ошибиться.</p>
                <div class="command-grid">
                        {command_buttons_html}
                </div>
        </section>
        <section class="panel wide">
                <span class="eyebrow">Маршрутизация</span>
                <h2 class="section-title">Списки обхода по протоколам и VPN</h2>
                <p class="section-subtitle">Здесь редактируются адреса и домены, которые будут отправляться через соответствующий протокол или VPN-правило.</p>
    </section>
    {unblock_lists_block}
    </div>
    </div>
</body>
</html>'''

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ['/', '/index.html', '/command']:
            self._send_html(self._build_form(_consume_web_flash_message()))
        else:
            self._send_html('<h1>404 Not Found</h1>', status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/set_proxy':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = parse_qs(body)
            proxy_type = data.get('proxy_type', ['none'])[0]
            ok, error = update_proxy(proxy_type)
            if ok:
                result = f'Режим бота установлен: {proxy_type}'
            else:
                result = f'⚠️ {error}'
            _invalidate_web_status_cache()
            _invalidate_key_status_cache()
            _set_web_flash_message(result)
            self._send_redirect('/')
            return

        if path == '/start':
            global bot_ready
            bot_ready = True
            _save_bot_autostart(True)
            _invalidate_web_status_cache()
            result = 'Бот запущен. Теперь он сразу начнет работу с Telegram API.'
            _set_web_flash_message(result)
            self._send_redirect('/')
            return

        if path == '/command':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = parse_qs(body)
            command = data.get('command', [''])[0]
            _, result = _start_web_command(command)
            _set_web_flash_message(result)
            self._send_redirect('/')
            return

        if path == '/save_unblock_list':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = parse_qs(body)
            list_name = data.get('list_name', [''])[0]
            content = data.get('content', [''])[0]
            try:
                result = _save_unblock_list(list_name, content)
            except Exception as exc:
                result = f'Ошибка сохранения списка: {exc}'
            _set_web_flash_message(result)
            self._send_redirect('/')
            return

        if path == '/append_socialnet':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = parse_qs(body)
            list_name = data.get('list_name', [''])[0]
            try:
                result = _append_socialnet_list(list_name)
            except Exception as exc:
                result = f'Ошибка добавления соцсетей: {exc}'
            _set_web_flash_message(result)
            self._send_redirect('/')
            return

        if path != '/install':
            self._send_html('<h1>404 Not Found</h1>', status=404)
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        data = parse_qs(body)
        key_type = data.get('type', [''])[0]
        key_value = data.get('key', [''])[0]
        result = 'Ключ установлен.'
        try:
            if key_type == 'shadowsocks':
                shadowsocks(key_value)
                result = _apply_installed_proxy('shadowsocks', key_value)
            elif key_type == 'vmess':
                vmess(key_value)
                result = _apply_installed_proxy('vmess', key_value)
            elif key_type == 'vless':
                vless(key_value)
                result = _apply_installed_proxy('vless', key_value)
            elif key_type == 'trojan':
                trojan(key_value)
                result = _apply_installed_proxy('trojan', key_value)
            elif key_type == 'tor':
                tormanually(key_value)
                os.system('/opt/etc/init.d/S35tor restart')
                result = '✅ Tor успешно обновлен.'
            else:
                result = 'Тип ключа не распознан.'
        except Exception as exc:
            result = f'Ошибка установки: {exc}'
        else:
            _invalidate_web_status_cache()
            _invalidate_key_status_cache()

        _set_web_flash_message(result)
        self._send_redirect('/')


def start_http_server():
    try:
        server_address = ('', int(browser_port))
        httpd = ThreadingHTTPServer(server_address, KeyInstallHTTPRequestHandler)
        httpd.daemon_threads = True
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
    except Exception as err:
        with open('/opt/etc/error.log', 'w') as errfile:
            errfile.write(str(err))


def wait_for_bot_start():
    global bot_ready
    while not bot_ready:
        time.sleep(1)


def _read_v2ray_key(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None


def _save_v2ray_key(file_path, key):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(key.strip())


def _parse_vmess_key(key):
    if not key.startswith('vmess://'):
        raise ValueError('Неверный протокол, ожидается vmess://')
    encodedkey = key[8:]
    try:
        decoded = base64.b64decode(encodedkey + '=' * (-len(encodedkey) % 4)).decode('utf-8')
    except Exception as exc:
        raise ValueError(f'Не удалось декодировать vmess-ключ: {exc}')
    try:
        data = json.loads(decoded.replace("'", '"'))
    except Exception as exc:
        raise ValueError(f'Неверный JSON в vmess-ключе: {exc}')
    if not data.get('add') or not data.get('port') or not data.get('id'):
        raise ValueError('В vmess-ключе нет server/port/id')
    if data.get('net') == 'grpc':
        service_name = data.get('serviceName') or data.get('grpcSettings', {}).get('serviceName')
        if not service_name:
            data['serviceName'] = data.get('add')
    return data


def _parse_vless_key(key):
    parsed = urlparse(key)
    if parsed.scheme != 'vless':
        raise ValueError('Неверный протокол, ожидается vless://')
    if not parsed.hostname:
        raise ValueError('В vless-ключе отсутствует адрес сервера')
    if not parsed.username:
        raise ValueError('В vless-ключе отсутствует UUID')
    params = parse_qs(parsed.query)
    address = parsed.hostname
    port = parsed.port or 443
    user_id = parsed.username
    security = params.get('security', ['none'])[0]
    encryption = params.get('encryption', ['none'])[0]
    flow = params.get('flow', [''])[0]
    host = params.get('host', [''])[0]
    if not address and host:
        address = host
    network = params.get('type', params.get('network', ['tcp']))[0]
    path = params.get('path', ['/'])[0]
    if path == '':
        path = '/'
    sni = params.get('sni', [''])[0] or host or address
    service_name = params.get('serviceName', [''])[0]
    public_key = params.get('pbk', params.get('publicKey', ['']))[0]
    short_id = params.get('sid', params.get('shortId', ['']))[0]
    fingerprint = params.get('fp', params.get('fingerprint', ['']))[0]
    spider_x = params.get('spx', params.get('spiderX', ['']))[0]
    alpn = params.get('alpn', [''])[0]
    if not service_name and (network == 'grpc' or security == 'reality'):
        service_name = address
    return {
        'address': address,
        'port': port,
        'id': user_id,
        'security': security,
        'encryption': encryption,
        'flow': flow,
        'host': host,
        'path': path,
        'sni': sni,
        'type': network,
        'serviceName': service_name,
        'publicKey': public_key,
        'shortId': short_id,
        'fingerprint': fingerprint,
        'spiderX': spider_x,
        'alpn': alpn
    }


def _build_v2ray_config(vmess_key=None, vless_key=None, shadowsocks_key=None, trojan_key=None):
    config_data = {
        'log': {
            'access': CORE_PROXY_ACCESS_LOG,
            'error': CORE_PROXY_ERROR_LOG,
            'loglevel': 'info'
        },
        'inbounds': [],
        'outbounds': [],
        'routing': {
            'domainStrategy': 'IPIfNonMatch',
            'rules': []
        }
    }

    if vmess_key:
        vmess_data = _parse_vmess_key(vmess_key)
        config_data['inbounds'].append({
            'port': int(localportvmess),
            'listen': '127.0.0.1',
            'protocol': 'socks',
            'settings': {
                'auth': 'noauth',
                'udp': True,
                'ip': '127.0.0.1'
            },
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'tag': 'in-vmess'
        })
        stream_settings = {'network': vmess_data.get('net', 'tcp')}
        tls_mode = vmess_data.get('tls', 'tls')
        if tls_mode in ['tls', 'xtls']:
            stream_settings['security'] = tls_mode
            stream_settings[f'{tls_mode}Settings'] = {
                'allowInsecure': True,
                'serverName': vmess_data.get('add', '')
            }
        else:
            stream_settings['security'] = 'none'
        if stream_settings['network'] == 'ws':
            stream_settings['wsSettings'] = {
                'path': vmess_data.get('path', '/'),
                'headers': {'Host': vmess_data.get('host', '')}
            }
        elif stream_settings['network'] == 'grpc':
            grpc_service = vmess_data.get('serviceName', '') or vmess_data.get('grpcSettings', {}).get('serviceName', '')
            stream_settings['grpcSettings'] = {
                'serviceName': grpc_service,
                'multiMode': False
            }
        config_data['outbounds'].append({
            'tag': 'proxy-vmess',
            'domainStrategy': 'UseIPv4',
            'protocol': 'vmess',
            'settings': {
                'vnext': [{
                    'address': vmess_data['add'],
                    'port': int(vmess_data['port']),
                    'users': [{
                        'id': vmess_data['id'],
                        'alterId': int(vmess_data.get('aid', 0)),
                        'email': 't@t.tt',
                        'security': 'auto'
                    }]
                }]
            },
            'streamSettings': stream_settings,
            'mux': {
                'enabled': True,
                'concurrency': -1,
                'xudpConcurrency': 16,
                'xudpProxyUDP443': 'reject'
            }
        })
        config_data['routing']['rules'].append({
            'type': 'field',
            'inboundTag': ['in-vmess'],
            'outboundTag': 'proxy-vmess',
            'enabled': True
        })

    if shadowsocks_key:
        server, port, method, password = _decode_shadowsocks_uri(shadowsocks_key)
        config_data['inbounds'].append({
            'port': int(localportsh_bot),
            'listen': '127.0.0.1',
            'protocol': 'socks',
            'settings': {
                'auth': 'noauth',
                'udp': True,
                'ip': '127.0.0.1'
            },
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'tag': 'in-shadowsocks'
        })
        config_data['outbounds'].append({
            'tag': 'proxy-shadowsocks',
            'protocol': 'shadowsocks',
            'settings': {
                'servers': [{
                    'address': server,
                    'port': int(port),
                    'method': method,
                    'password': password,
                    'level': 0
                }]
            }
        })
        config_data['routing']['rules'].append({
            'type': 'field',
            'inboundTag': ['in-shadowsocks'],
            'outboundTag': 'proxy-shadowsocks',
            'enabled': True
        })

    if vless_key:
        vless_data = _parse_vless_key(vless_key)
        config_data['inbounds'].append({
            'port': int(localportvless),
            'listen': '127.0.0.1',
            'protocol': 'socks',
            'settings': {
                'auth': 'noauth',
                'udp': True,
                'ip': '127.0.0.1'
            },
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'tag': 'in-vless'
        })
        config_data['inbounds'].append({
            'port': int(localportvless_transparent),
            'listen': '0.0.0.0',
            'protocol': 'dokodemo-door',
            'settings': {
                'network': 'tcp',
                'followRedirect': True
            },
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'tag': 'in-vless-transparent'
        })
        network = vless_data.get('type', 'tcp')
        if network == '':
            network = 'tcp'
        stream_settings = {'network': network}
        security = vless_data.get('security', 'none')
        if security in ['tls', 'xtls']:
            stream_settings['security'] = security
            stream_settings[f'{security}Settings'] = {
                'allowInsecure': True,
                'serverName': vless_data.get('sni', '')
            }
        else:
            stream_settings['security'] = 'none'
        if network == 'ws':
            stream_settings['wsSettings'] = {
                'path': vless_data.get('path', '/'),
                'headers': {'Host': vless_data.get('host', '')}
            }
        elif network == 'grpc':
            stream_settings['grpcSettings'] = {
                'serviceName': vless_data.get('serviceName', ''),
                'multiMode': False
            }
        elif security == 'reality':
            stream_settings['security'] = 'reality'
            stream_settings['realitySettings'] = {
                'serverName': vless_data.get('sni', '') or vless_data.get('host', '') or vless_data.get('address', ''),
                'publicKey': vless_data.get('publicKey', ''),
                'shortId': vless_data.get('shortId', ''),
                'fingerprint': vless_data.get('fingerprint', 'chrome'),
                'spiderX': vless_data.get('spiderX', '/')
            }
            if vless_data.get('alpn'):
                stream_settings['realitySettings']['alpn'] = [item.strip() for item in vless_data['alpn'].split(',') if item.strip()]
        config_data['outbounds'].append({
            'tag': 'proxy-vless',
            'domainStrategy': 'UseIPv4',
            'protocol': 'vless',
            'settings': {
                'vnext': [{
                    'address': vless_data.get('address', vless_data.get('host', '')),
                    'port': int(vless_data['port']),
                    'users': [{
                        'id': vless_data['id'],
                        'encryption': vless_data.get('encryption', 'none'),
                        'flow': vless_data.get('flow', ''),
                        'level': 0
                    }]
                }]
            },
            'streamSettings': stream_settings
        })
        config_data['routing']['rules'].append({
            'type': 'field',
            'inboundTag': ['in-vless', 'in-vless-transparent'],
            'outboundTag': 'proxy-vless',
            'enabled': True
        })

    if trojan_key:
        trojan_data = _parse_trojan_key(trojan_key)
        config_data['inbounds'].append({
            'port': int(localporttrojan_bot),
            'listen': '127.0.0.1',
            'protocol': 'socks',
            'settings': {
                'auth': 'noauth',
                'udp': True,
                'ip': '127.0.0.1'
            },
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'tag': 'in-trojan'
        })
        trojan_stream = {
            'network': trojan_data.get('type', 'tcp') or 'tcp',
            'security': 'none'
        }
        if trojan_data.get('security', 'tls') == 'tls':
            trojan_stream['security'] = 'tls'
            trojan_stream['tlsSettings'] = {
                'allowInsecure': True,
                'serverName': trojan_data.get('sni') or trojan_data.get('host') or trojan_data.get('address', ''),
                'fingerprint': trojan_data.get('fingerprint', 'chrome')
            }
            if trojan_data.get('alpn'):
                trojan_stream['tlsSettings']['alpn'] = [item.strip() for item in trojan_data['alpn'].split(',') if item.strip()]
        if trojan_stream['network'] == 'ws':
            trojan_stream['wsSettings'] = {
                'path': trojan_data.get('path', '/'),
                'headers': {'Host': trojan_data.get('host') or trojan_data.get('sni') or trojan_data.get('address', '')}
            }
        elif trojan_stream['network'] == 'grpc':
            trojan_stream['grpcSettings'] = {
                'serviceName': trojan_data.get('serviceName', ''),
                'multiMode': False
            }
        config_data['outbounds'].append({
            'tag': 'proxy-trojan',
            'protocol': 'trojan',
            'settings': {
                'servers': [{
                    'address': trojan_data['address'],
                    'port': int(trojan_data['port']),
                    'password': trojan_data['password'],
                    'level': 0
                }]
            },
            'streamSettings': trojan_stream
        })
        config_data['routing']['rules'].append({
            'type': 'field',
            'inboundTag': ['in-trojan'],
            'outboundTag': 'proxy-trojan',
            'enabled': True
        })

    if config_data['outbounds']:
        config_data['outbounds'].append({'protocol': 'freedom', 'tag': 'direct'})
        config_data['routing']['rules'].append({
            'type': 'field',
            'port': '0-65535',
            'outboundTag': 'direct',
            'enabled': True
        })

    return config_data


def _write_v2ray_config(vmess_key=None, vless_key=None, shadowsocks_key=None, trojan_key=None):
    config_json = _build_v2ray_config(vmess_key, vless_key, shadowsocks_key, trojan_key)
    os.makedirs(CORE_PROXY_CONFIG_DIR, exist_ok=True)
    with open(CORE_PROXY_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, ensure_ascii=False, indent=2)


def _write_all_proxy_core_config():
    _write_v2ray_config(
        _read_v2ray_key(VMESS_KEY_PATH),
        _read_v2ray_key(VLESS_KEY_PATH),
        _load_shadowsocks_key(),
        _load_trojan_key(),
    )


def vless(key):
    _parse_vless_key(key)
    _save_v2ray_key(VLESS_KEY_PATH, key)
    _write_all_proxy_core_config()


def vmess(key):
    _parse_vmess_key(key)
    _save_v2ray_key(VMESS_KEY_PATH, key)
    _write_all_proxy_core_config()

def trojan(key):
    trojan_data = _parse_trojan_key(key)
    config = {
        'run_type': 'nat',
        'local_addr': '::',
        'local_port': int(localporttrojan),
        'remote_addr': trojan_data['address'],
        'remote_port': int(trojan_data['port']),
        'password': [trojan_data['password']],
        'ssl': {
            'verify': False,
            'verify_hostname': False,
        }
    }
    with open('/opt/etc/trojan/config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, separators=(',', ':'))
    _write_all_proxy_core_config()

def _decode_shadowsocks_uri(key):
    if not key.startswith('ss://'):
        raise ValueError('Неверный протокол, ожидается ss://')
    payload = key[5:]
    payload, _, _ = payload.partition('#')
    payload, _, _ = payload.partition('?')
    if '@' in payload:
        left, right = payload.rsplit('@', 1)
        host_part = right
        if ':' not in host_part:
            raise ValueError('Не удалось определить host:port в Shadowsocks-ключе')
        server, port = host_part.split(':', 1)
        try:
            decoded = base64.urlsafe_b64decode(left + '=' * (-len(left) % 4)).decode('utf-8')
            if ':' not in decoded:
                raise ValueError('Неверный формат декодированного payload Shadowsocks')
            method, password = decoded.split(':', 1)
        except Exception:
            decoded = unquote(left)
            if ':' not in decoded:
                raise ValueError('Неверный формат Shadowsocks credentials')
            method, password = decoded.split(':', 1)
    else:
        decoded = base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)).decode('utf-8')
        if '@' not in decoded:
            raise ValueError('Не удалось разобрать Shadowsocks-ключ')
        creds, host_part = decoded.rsplit('@', 1)
        if ':' not in host_part or ':' not in creds:
            raise ValueError('Неверный формат раскодированного Shadowsocks-URI')
        server, port = host_part.split(':', 1)
        method, password = creds.split(':', 1)
    return server, port, method, password


def shadowsocks(key=None):
    server, port, method, password = _decode_shadowsocks_uri(key.strip())
    config = {
        'server': [server],
        'mode': 'tcp_and_udp',
        'server_port': int(port),
        'password': password,
        'timeout': 86400,
        'method': method,
        'local_address': '::',
        'local_port': int(localportsh),
        'fast_open': False,
        'ipv6_first': True
    }
    with open('/opt/etc/shadowsocks.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    _write_all_proxy_core_config()

def tormanually(bridges):
    # global localporttor, dnsporttor
    f = open('/opt/etc/tor/torrc', 'w')
    f.write('User root\n\
PidFile /opt/var/run/tor.pid\n\
ExcludeExitNodes {RU},{UA},{AM},{KG},{BY}\n\
StrictNodes 1\n\
TransPort 0.0.0.0:' + localporttor + '\n\
ExitRelay 0\n\
ExitPolicy reject *:*\n\
ExitPolicy reject6 *:*\n\
GeoIPFile /opt/share/tor/geoip\n\
GeoIPv6File /opt/share/tor/geoip6\n\
DataDirectory /opt/tmp/tor\n\
VirtualAddrNetwork 10.254.0.0/16\n\
DNSPort 127.0.0.1:' + dnsporttor + '\n\
AutomapHostsOnResolve 1\n\
UseBridges 1\n\
ClientTransportPlugin obfs4 exec /opt/sbin/obfs4proxy managed\n' + bridges.replace("obfs4", "Bridge obfs4"))
    f.close()

def tor():
    # global appapiid, appapihash
    # global localporttor, dnsporttor
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    f = open('/opt/etc/tor/torrc', 'w')
    with TelegramClient('GetBridgesBot', appapiid, appapihash) as client:
        client.send_message('GetBridgesBot', '/bridges')
    with TelegramClient('GetBridgesBot', appapiid, appapihash) as client:
        for message1 in client.iter_messages('GetBridgesBot'):
            f.write('User root\n\
PidFile /opt/var/run/tor.pid\n\
ExcludeExitNodes {RU},{UA},{AM},{KG},{BY}\n\
StrictNodes 1\n\
TransPort 0.0.0.0:' + localporttor + '\n\
ExitRelay 0\n\
ExitPolicy reject *:*\n\
ExitPolicy reject6 *:*\n\
GeoIPFile /opt/share/tor/geoip\n\
GeoIPv6File /opt/share/tor/geoip6\n\
DataDirectory /opt/tmp/tor\n\
VirtualAddrNetwork 10.254.0.0/16\n\
DNSPort 127.0.0.1:' + dnsporttor + '\n\
AutomapHostsOnResolve 1\n\
UseBridges 1\n\
ClientTransportPlugin obfs4 exec /opt/sbin/obfs4proxy managed\n'
                    + message1.text.replace("Your bridges:\n", "").replace("obfs4", "Bridge obfs4"))
            f.close()
            break


def main():
    global proxy_mode, bot_polling
    _daemonize_process()
    try:
        _write_all_proxy_core_config()
        os.system(CORE_PROXY_SERVICE_SCRIPT + ' restart')
    except Exception as exc:
        with open('/opt/etc/error.log', 'a', encoding='utf-8', errors='ignore') as fl:
            fl.write(f'Не удалось пересобрать core proxy config при старте: {exc}\n')
    if _load_bot_autostart():
        globals()['bot_ready'] = True
    proxy_mode = _load_proxy_mode()
    ok, error = update_proxy(proxy_mode)
    if not ok:
        proxy_mode = config.default_proxy_mode
        update_proxy(proxy_mode)
    elif proxy_mode in ['shadowsocks', 'vmess', 'vless', 'trojan']:
        startup_settings = {
            'shadowsocks': localportsh_bot,
            'vmess': localportvmess,
            'vless': localportvless,
            'trojan': localporttrojan_bot,
        }
        startup_port = startup_settings.get(proxy_mode)
        endpoint_ok, endpoint_message = _check_local_proxy_endpoint(proxy_mode, startup_port)
        if not endpoint_ok:
            with open('/opt/etc/error.log', 'a', encoding='utf-8', errors='ignore') as fl:
                fl.write(f'Прокси-режим {proxy_mode} отключён при старте: {endpoint_message}\n')
            proxy_mode = 'none'
            update_proxy('none')
        else:
            api_status = check_telegram_api(retries=0, retry_delay=0, connect_timeout=8, read_timeout=10)
            if not api_status.startswith('✅'):
                with open('/opt/etc/error.log', 'a', encoding='utf-8', errors='ignore') as fl:
                    fl.write(f'Прокси-режим {proxy_mode} не подтверждён при старте: {api_status}\n')
    start_http_server()
    wait_for_bot_start()
    while True:
        try:
            bot_polling = True
            bot.infinity_polling(timeout=60, long_polling_timeout=50)
        except Exception as err:
            bot_polling = False
            with open('/opt/etc/error.log', 'a', encoding='utf-8', errors='ignore') as fl:
                fl.write(str(err) + '\n')
            time.sleep(5)
        else:
            bot_polling = False
            time.sleep(2)


if __name__ == '__main__':
    main()
