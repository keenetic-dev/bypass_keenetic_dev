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
    'shadowsocks': f'socks5h://127.0.0.1:{localportsh}',
    'vmess': f'socks5h://127.0.0.1:{localportvmess}',
    'vless': f'socks5h://127.0.0.1:{localportvless}',
    'trojan': None,
}
proxy_supports_http = {
    'none': True,
    'shadowsocks': True,
    'vmess': True,
    'vless': True,
    'trojan': False,
}
web_status_cache = {
    'timestamp': 0,
    'data': None,
}


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


def _load_bot_autostart():
    try:
        with open(BOT_AUTOSTART_FILE, 'r', encoding='utf-8') as file:
            return file.read().strip() == '1'
    except Exception:
        return False


def _invalidate_web_status_cache():
    web_status_cache['timestamp'] = 0
    web_status_cache['data'] = None


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
        'path': params.get('path', ['/'])[0] or '/'
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
    if key_type in ['shadowsocks', 'vmess', 'vless']:
        if _wait_for_socks5_handshake(port, timeout=12):
            return True, f'Локальный SOCKS-порт 127.0.0.1:{port} отвечает как SOCKS5.'
        if _port_is_listening(port):
            return False, f'Локальный порт 127.0.0.1:{port} открыт, но не отвечает как SOCKS5.'
        return False, f'Локальный порт 127.0.0.1:{port} недоступен.'
    if key_type == 'trojan':
        if _port_is_listening(port) or _wait_for_port(None, port, timeout=3):
            return True, f'Локальный порт Trojan 127.0.0.1:{port} открыт.'
        return False, f'Локальный порт Trojan 127.0.0.1:{port} недоступен.'
    return True, ''


def _apply_installed_proxy(key_type, key_value):
    settings = {
        'shadowsocks': {
            'label': 'Shadowsocks',
            'port': localportsh,
            'restart_cmd': '/opt/etc/init.d/S22shadowsocks restart',
            'startup_wait': 3,
        },
        'vmess': {
            'label': 'Vmess',
            'port': localportvmess,
            'restart_cmd': CORE_PROXY_SERVICE_SCRIPT + ' restart',
            'startup_wait': 18,
        },
        'vless': {
            'label': 'Vless',
            'port': localportvless,
            'restart_cmd': CORE_PROXY_SERVICE_SCRIPT + ' restart',
            'startup_wait': 18,
        },
        'trojan': {
            'label': 'Trojan',
            'port': localporttrojan,
            'restart_cmd': '/opt/etc/init.d/S22trojan restart',
            'startup_wait': 3,
        }
    }
    current = settings[key_type]
    os.system(current['restart_cmd'])
    time.sleep(current['startup_wait'])

    ok, error = update_proxy(key_type)
    diagnostics = _build_proxy_diagnostics(key_type, key_value)
    if not ok:
        return f'⚠️ {current["label"]} ключ сохранён, но режим бота не применён: {error}. {diagnostics}'.strip()

    if not _ensure_service_port(current['port'], current['restart_cmd'], retries=2, sleep_after_restart=5):
        update_proxy('none')
        return (f'⚠️ {current["label"]} ключ сохранён, но локальный порт 127.0.0.1:{current["port"]} '
                f'не поднялся. Бот переключён в режим none. {diagnostics}').strip()

    endpoint_ok, endpoint_message = _check_local_proxy_endpoint(key_type, current['port'])
    if not endpoint_ok:
        update_proxy('none')
        return (f'⚠️ {current["label"]} ключ сохранён, но {endpoint_message} '
                f'Бот переключён в режим none. {diagnostics}').strip()

    if proxy_supports_http.get(key_type, False):
        api_status = check_telegram_api(retries=1, retry_delay=2, connect_timeout=10, read_timeout=15)
        if api_status.startswith('✅'):
            return (f'✅ {current["label"]} ключ сохранён. {endpoint_message} '
                    f'Бот переведён в режим {current["label"]}. {api_status}').strip()
        return (f'⚠️ {current["label"]} ключ сохранён. {endpoint_message} '
                f'Бот переведён в режим {current["label"]}, но Telegram API не проходит через этот прокси. '
                f'{api_status} {diagnostics}').strip()

    return (f'⚠️ {current["label"]} ключ сохранён. {endpoint_message} '
            f'Бот переведён в режим {current["label"]}, но Telegram API в текущей конфигурации '
            f'через этот режим не проверяется и не используется как HTTP/SOCKS proxy. {diagnostics}').strip()


def update_proxy(proxy_type):
    global proxy_mode
    proxy_url = proxy_settings.get(proxy_type)
    if proxy_type != 'trojan' and proxy_url and proxy_url.startswith('socks') and not _has_socks_support():
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
    return True, None


def check_telegram_api(retries=2, retry_delay=7, connect_timeout=30, read_timeout=45):
    url = f'https://api.telegram.org/bot{token}/getMe'
    proxies = telebot.apihelper.proxy if getattr(telebot.apihelper, 'proxy', None) else None
    last_result = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, timeout=(connect_timeout, read_timeout), proxies=proxies)
            response.raise_for_status()
            data = response.json()
            if data.get('ok'):
                return '✅ Доступ к api.telegram.org подтверждён.'
            return f'⚠️ Telegram API ответил: {data.get("description", "Не удалось определить причину")} '
        except requests.exceptions.RequestException as exc:
            error_text = str(exc)
            if 'Missing dependencies for SOCKS support' in error_text:
                return ('❌ Не удалось подключиться к Telegram API: отсутствует поддержка SOCKS (PySocks). '
                        'Установите python3-pysocks или используйте режим без SOCKS.')
            if proxy_mode == 'trojan':
                return ('❌ Не удалось подключиться к Telegram API через Trojan: текущая локальная конфигурация не поддерживает HTTPS/HTTP proxy '
                        'в этом режиме. Используйте Shadowsocks, Vmess или Vless для прокси Telegram API.')
            if 'Connection refused' in error_text or 'SOCKSHTTPSConnection' in error_text:
                if proxy_mode in ['shadowsocks', 'vmess', 'vless']:
                    port = {
                        'shadowsocks': localportsh,
                        'vmess': localportvmess,
                        'vless': localportvless
                    }.get(proxy_mode)
                    if port and not _check_socks5_handshake(port):
                        return ('❌ Не удалось подключиться к Telegram API: соединение через SOCKS-прокси отказано. '
                                'Локальный порт отвечает, но не как SOCKS5. Проверьте конфигурацию прокси-сервиса и логи.')
                last_result = ('❌ Не удалось подключиться к Telegram API: соединение через SOCKS-прокси отказано. '
                               'Проверьте, что локальный прокси-сервис запущен и порт доступен.')
            else:
                last_result = f'❌ Не удалось подключиться к Telegram API: {exc}'
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
    if proxy_mode in ['shadowsocks', 'vmess', 'vless']:
        port = {
            'shadowsocks': localportsh,
            'vmess': localportvmess,
            'vless': localportvless
        }.get(proxy_mode)
        if port:
            socks_ok = _check_socks5_handshake(port)
            socks_details = f'Локальный SOCKS {proxy_mode} 127.0.0.1:{port}: {"доступен" if socks_ok else "не отвечает как SOCKS5"}'
    api_status = check_telegram_api(retries=0, retry_delay=0, connect_timeout=2, read_timeout=3)
    snapshot = {
        'state_label': state_label,
        'proxy_mode': proxy_mode,
        'api_status': api_status,
        'socks_details': socks_details
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
                shadowsocks(message.text)
                time.sleep(2)
                os.system('/opt/etc/init.d/S22shadowsocks restart')
                level = 0
                bot.send_message(message.chat.id, '✅ Успешно обновлено', reply_markup=main)
                # return

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
                vmess(message.text)
                os.system(CORE_PROXY_SERVICE_SCRIPT + ' restart')
                level = 0
                bot.send_message(message.chat.id, '✅ Успешно обновлено', reply_markup=main)

            if level == 10:
                trojan(message.text)
                os.system('/opt/etc/init.d/S22trojan restart')
                level = 0
                bot.send_message(message.chat.id, '✅ Успешно обновлено', reply_markup=main)

            if level == 11:
                vless(message.text)
                os.system(CORE_PROXY_SERVICE_SCRIPT + ' restart')
                level = 0
                bot.send_message(message.chat.id, '✅ Успешно обновлено', reply_markup=main)

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
                                 'Введите мосты Tor или другие ключи на странице.', reply_markup=main)
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
                item2 = types.KeyboardButton("Tor")
                item3 = types.KeyboardButton("Vmess")
                item4 = types.KeyboardButton("Vless")
                item5 = types.KeyboardButton("Trojan")
                item6 = types.KeyboardButton("Где брать ключи❔")
                item7 = types.KeyboardButton("🌐 Через браузер")
                markup.add(item1, item2)
                markup.add(item3, item4)
                markup.add(item5)
                markup.add(item6)
                markup.add(item7)
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

    def _build_form(self, message=''):
        status = _web_status_snapshot()
        message_block = ''
                if message:
            safe_message = html.escape(message)
            message_block = f'''<div class="notice notice-result">
  <strong>Результат</strong>
    <pre class="log-output">{safe_message}</pre>
</div>'''
        socks_block = ''
        if status['socks_details']:
            socks_block = f'<p class="status-note">{html.escape(status["socks_details"])}' + '</p>'
        status_block = f'''<div class="status-grid">
    <div class="status-card">
        <span class="status-label">Процесс бота</span>
        <strong class="status-value">{html.escape(status['state_label'])}</strong>
    </div>
    <div class="status-card">
        <span class="status-label">Текущий режим</span>
        <strong class="status-value">{html.escape(status['proxy_mode'])}</strong>
    </div>
</div>
<div class="notice notice-status">
    <strong>Связь с Telegram API</strong>
    <p>{html.escape(status['api_status'])}</p>
    {socks_block}
</div>'''
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Установка ключей VPN</title>
    <style>
        :root{{
            --bg:#111827;
            --bg-accent:#1b2435;
            --surface:#1f2937;
            --surface-soft:#243044;
            --border:#334155;
            --text:#e5eefc;
            --muted:#9fb0c8;
            --primary:#4f8cff;
            --primary-hover:#6aa0ff;
            --success-bg:#123227;
            --success-border:#2f7d57;
            --warn-bg:#3a2d14;
            --warn-border:#ae7b21;
            --shadow:0 20px 45px rgba(2, 6, 23, 0.28);
        }}
        *{{box-sizing:border-box;}}
        body{{
            margin:0;
            font-family:Segoe UI,Helvetica,Arial,sans-serif;
            color:var(--text);
            background:radial-gradient(circle at top, #22304a 0%, var(--bg) 52%, #0f172a 100%);
            padding:18px;
        }}
        .shell{{max-width:1080px;margin:0 auto;}}
        .hero{{margin-bottom:20px;padding:24px;border:1px solid rgba(148,163,184,.18);border-radius:22px;background:linear-gradient(145deg, rgba(31,41,55,.96), rgba(17,24,39,.92));box-shadow:var(--shadow);}}
        h1{{margin:0 0 12px;font-size:clamp(28px,5vw,42px);line-height:1.05;letter-spacing:-0.03em;color:#f8fbff;}}
        h2{{margin:0 0 14px;font-size:20px;color:#f8fbff;}}
        p{{margin:0 0 10px;line-height:1.55;color:var(--muted);}}
        .hero strong{{color:#f8fbff;}}
        .layout{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}}
        section{{padding:18px;border:1px solid rgba(148,163,184,.16);border-radius:18px;background:linear-gradient(180deg, rgba(31,41,55,.96), rgba(23,33,49,.92));box-shadow:var(--shadow);}}
        form{{display:grid;gap:12px;}}
        input,textarea,select{{width:100%;padding:13px 14px;border-radius:12px;border:1px solid var(--border);background:var(--surface-soft);color:var(--text);font-size:16px;outline:none;}}
        textarea{{min-height:138px;resize:vertical;}}
        input::placeholder,textarea::placeholder{{color:#7f93b0;}}
        button{{padding:13px 16px;border:none;border-radius:12px;background:linear-gradient(135deg, var(--primary), #2f6ae6);color:#fff;font-size:15px;font-weight:600;cursor:pointer;transition:transform .15s ease, filter .15s ease;}}
        button:hover{{filter:brightness(1.08);transform:translateY(-1px);}}
        .status-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:14px;}}
        .status-card{{padding:14px;border-radius:14px;background:rgba(59,130,246,.08);border:1px solid rgba(96,165,250,.18);}}
        .status-label{{display:block;margin-bottom:8px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#90a5c4;}}
        .status-value{{font-size:16px;color:#f8fbff;}}
        .notice{{padding:16px;border-radius:16px;margin-bottom:18px;}}
        .notice strong{{display:block;margin-bottom:8px;color:#fff;}}
        .notice-result{{background:var(--warn-bg);border:1px solid var(--warn-border);}}
        .notice-status{{background:var(--success-bg);border:1px solid var(--success-border);}}
        .status-note{{margin-top:10px;color:#d6e5fb;}}
        .log-output{{margin:0;white-space:pre-wrap;word-break:break-word;font:13px/1.45 Consolas,Monaco,monospace;color:#f8fbff;}}
        .wide{{grid-column:1 / -1;}}
        @media (max-width: 760px){{
            body{{padding:12px;}}
            .hero{{padding:18px;border-radius:18px;}}
            .layout{{grid-template-columns:1fr;gap:12px;}}
            .status-grid{{grid-template-columns:1fr;}}
            section{{padding:16px;border-radius:16px;}}
            button,input,textarea,select{{font-size:16px;}}
        }}
    </style>
</head>
<body>
    <div class="shell">
    <div class="hero">
        <h1>Установка ключей VPN</h1>
        <p>Страница показывает не только состояние процесса, но и реальный статус связи с Telegram API.</p>
        <p><strong>Вставляйте ключ полной строкой, как в Telegram.</strong></p>
    </div>
    {message_block}
    <div class="layout">
    <section class="wide">
    <h2>Протокол бота</h2>
    <form method="post" action="/set_proxy">
      <select name="proxy_type">
        <option value="none"{' selected' if proxy_mode == 'none' else ''}>Без VPN (по умолчанию)</option>
        <option value="shadowsocks"{' selected' if proxy_mode == 'shadowsocks' else ''}>Shadowsocks</option>
        <option value="vmess"{' selected' if proxy_mode == 'vmess' else ''}>Vmess</option>
        <option value="vless"{' selected' if proxy_mode == 'vless' else ''}>Vless</option>
        <option value="trojan"{' selected' if proxy_mode == 'trojan' else ''}>Trojan</option>
      </select>
      <button type="submit">Использовать для бота</button>
    </form>
        <p>Смените режим и затем проверьте блок статуса ниже. Он покажет реальную доступность Telegram API, а не только запуск процесса.</p>
  </section>
    <section>
    <h2>Shadowsocks</h2>
    <form method="post" action="/install">
      <input type="hidden" name="type" value="shadowsocks">
      <input type="text" name="key" placeholder="shadowsocks://..." required>
      <button type="submit">Установить Shadowsocks</button>
    </form>
  </section>
  <section>
    <h2>Vmess</h2>
    <form method="post" action="/install">
      <input type="hidden" name="type" value="vmess">
      <input type="text" name="key" placeholder="vmess://..." required>
      <button type="submit">Установить Vmess</button>
    </form>
  </section>
  <section>
    <h2>Vless</h2>
    <form method="post" action="/install">
      <input type="hidden" name="type" value="vless">
      <input type="text" name="key" placeholder="vless://..." required>
      <button type="submit">Установить Vless</button>
    </form>
  </section>
  <section>
    <h2>Trojan</h2>
    <form method="post" action="/install">
      <input type="hidden" name="type" value="trojan">
      <input type="text" name="key" placeholder="trojan://..." required>
      <button type="submit">Установить Trojan</button>
    </form>
  </section>
    <section class="wide">
    <h2>Статус бота</h2>
        {status_block}
        <p>Если процесс поднят, но Telegram API недоступен, бот не сможет отвечать в чате. Проверяйте этот блок после смены ключа или режима.</p>
  </section>
  <section>
    <h2>Tor вручную</h2>
    <form method="post" action="/install">
      <input type="hidden" name="type" value="tor">
      <textarea name="key" rows="6" placeholder="Bridge obfs4 ..." required></textarea>
      <button type="submit">Установить Tor</button>
    </form>
  </section>
  <section>
    <h2>Запустить бот</h2>
    <p>После установки ключей нажмите кнопку, чтобы бот начал работу.</p>
    <form method="post" action="/start">
      <button type="submit">Запустить бота</button>
    </form>
  </section>
    <section class="wide">
        <h2>Команды установки и сервиса</h2>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="install_fork">
            <button type="submit">Установить из форка</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="install_original">
            <button type="submit">Установить оригинальную версию</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="update">
            <button type="submit">Обновить через форк</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="remove">
            <button type="submit">Удалить компоненты</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="restart_services">
            <button type="submit">Перезапустить сервисы</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="dns_on">
            <button type="submit">DNS Override ВКЛ</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="dns_off">
            <button type="submit">DNS Override ВЫКЛ</button>
        </form>
        <form method="post" action="/command">
            <input type="hidden" name="command" value="reboot">
            <button type="submit">Перезагрузить роутер</button>
        </form>
    </section>
    </div>
    </div>
</body>
</html>'''

    def do_GET(self):
        if self.path in ['/', '/index.html']:
            self._send_html(self._build_form())
        else:
            self._send_html('<h1>404 Not Found</h1>', status=404)

    def do_POST(self):
        if self.path == '/set_proxy':
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
            self._send_html(self._build_form(result))
            return

        if self.path == '/start':
            global bot_ready
            bot_ready = True
            _save_bot_autostart(True)
            _invalidate_web_status_cache()
            result = 'Бот запущен. Теперь бот начал polling Telegram API.'
            self._send_html(self._build_form(result))
            return

        if self.path == '/command':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = parse_qs(body)
            command = data.get('command', [''])[0]
            try:
                result = _run_web_command(command)
            except Exception as exc:
                result = f'Ошибка выполнения команды: {exc}'
            else:
                _invalidate_web_status_cache()
            self._send_html(self._build_form(result))
            return

        if self.path != '/install':
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

        self._send_html(self._build_form(result))


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
        decoded = base64.b64decode(encodedkey).decode('utf-8')
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


def _build_v2ray_config(vmess_key=None, vless_key=None):
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
            'inboundTag': ['in-vless'],
            'outboundTag': 'proxy-vless',
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


def _write_v2ray_config(vmess_key=None, vless_key=None):
    config_json = _build_v2ray_config(vmess_key, vless_key)
    os.makedirs(CORE_PROXY_CONFIG_DIR, exist_ok=True)
    with open(CORE_PROXY_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, ensure_ascii=False, indent=2)


def vless(key):
    _parse_vless_key(key)
    _save_v2ray_key(VLESS_KEY_PATH, key)
    current_vmess = _read_v2ray_key(VMESS_KEY_PATH)
    _write_v2ray_config(current_vmess, key)


def vmess(key):
    _parse_vmess_key(key)
    _save_v2ray_key(VMESS_KEY_PATH, key)
    current_vless = _read_v2ray_key(VLESS_KEY_PATH)
    _write_v2ray_config(key, current_vless)

def trojan(key):
    # global appapiid, appapihash, password, localporttrojan
    key = key.split('//')[1]
    pw = key.split('@')[0]
    key = key.replace(pw + "@", "", 1)
    host = key.split(':')[0]
    key = key.replace(host + ":", "", 1)
    port = key.split('?')[0].split('#')[0]
    f = open('/opt/etc/trojan/config.json', 'w')
    sh = '{"run_type":"nat","local_addr":"::","local_port":' \
         + str(localporttrojan) + ',"remote_addr":"' + host + '","remote_port":' + port + \
         ',"password":["' + pw + '"],"ssl":{"verify":false,"verify_hostname":false}}'
    f.write(sh)
    f.close()

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
        'local_address': '127.0.0.1',
        'local_port': int(localportsh),
        'fast_open': False,
        'ipv6_first': True
    }
    with open('/opt/etc/shadowsocks.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

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
    if _load_bot_autostart():
        globals()['bot_ready'] = True
    proxy_mode = _load_proxy_mode()
    ok, error = update_proxy(proxy_mode)
    if not ok:
        proxy_mode = config.default_proxy_mode
        update_proxy(proxy_mode)
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
