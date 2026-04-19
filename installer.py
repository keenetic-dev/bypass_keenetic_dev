#!/usr/bin/python3

import html
import os
import re
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


BOT_DIR = '/opt/etc/bot'
BOT_CONFIG_PATH = os.path.join(BOT_DIR, 'bot_config.py')
LEGACY_CONFIG_PATH = '/opt/etc/bot_config.py'
BOT_MAIN_PATH = os.path.join(BOT_DIR, 'main.py')
LEGACY_MAIN_PATH = '/opt/etc/bot.py'
BOT_SERVICE_PATH = '/opt/etc/init.d/S99telegram_bot'
INSTALLER_SERVICE_PATH = '/opt/etc/init.d/S98telegram_bot_installer'
DEFAULT_BROWSER_PORT = int(os.environ.get('BYPASS_INSTALLER_PORT', '8080'))
DEFAULT_FORK_REPO_OWNER = 'andruwko73'
DEFAULT_FORK_REPO_NAME = 'bypass_keenetic'
HOST = '0.0.0.0'


def detect_router_ip():
    try:
        output = subprocess.check_output(
            ['sh', '-c', "ip -4 addr show br0 | grep -Eo '([0-9]{1,3}\\.){3}[0-9]{1,3}' | head -n1"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if output:
            return output
    except Exception:
        pass
    return '192.168.1.1'


def ensure_legacy_path(source_path, legacy_path):
    try:
        if os.path.islink(legacy_path) or os.path.exists(legacy_path):
            os.remove(legacy_path)
    except Exception:
        pass

    try:
        os.symlink(source_path, legacy_path)
        return
    except Exception:
        pass

    shutil.copyfile(source_path, legacy_path)


def escape_python(value):
    return value.replace('\\', '\\\\').replace("'", "\\'")


def build_config(form):
    router_ip = form.get('routerip', detect_router_ip()).strip() or detect_router_ip()
    browser_port = form.get('browser_port', str(DEFAULT_BROWSER_PORT)).strip() or str(DEFAULT_BROWSER_PORT)
    fork_repo_owner = DEFAULT_FORK_REPO_OWNER
    fork_repo_name = DEFAULT_FORK_REPO_NAME
    fork_button_label = f'Fork by {fork_repo_owner}'
    default_proxy_mode = form.get('default_proxy_mode', 'none').strip() or 'none'

    return f"""# ВЕРСИЯ СКРИПТА 2.2.1

token = '{escape_python(form['token'])}'
usernames = ['{escape_python(form['username'])}']

appapiid = '{escape_python(form['appapiid'])}'
appapihash = '{escape_python(form['appapihash'])}'
routerip = '{escape_python(router_ip)}'
browser_port = '{escape_python(browser_port)}'
fork_repo_owner = '{escape_python(fork_repo_owner)}'
fork_repo_name = '{escape_python(fork_repo_name)}'
fork_button_label = '{escape_python(fork_button_label)}'

vpn_allowed=\"IKE|SSTP|OpenVPN|Wireguard|L2TP\"

localportsh = '1082'
dnsporttor = '9053'
localporttor = '9141'
localportvmess = '10810'
localportvless = '10811'
localporttrojan = '10829'
default_proxy_mode = '{escape_python(default_proxy_mode)}'
dnsovertlsport = '40500'
dnsoverhttpsport = '40508'
"""


def validate_form(form):
    required = ['token', 'username', 'appapiid', 'appapihash']
    missing = [key for key in required if not form.get(key, '').strip()]
    if missing:
        return False, 'Не заполнены обязательные поля: ' + ', '.join(missing)

    if not re.fullmatch(r'\d{5,}', form.get('appapiid', '').strip()):
        return False, 'Поле appapiid должно содержать только цифры.'

    browser_port = form.get('browser_port', '').strip()
    if browser_port and not re.fullmatch(r'\d{2,5}', browser_port):
        return False, 'Поле browser_port должно содержать номер порта.'

    return True, ''


def write_config(form):
    os.makedirs(BOT_DIR, exist_ok=True)
    config_text = build_config(form)
    with open(BOT_CONFIG_PATH, 'w', encoding='utf-8') as file:
        file.write(config_text)
    os.chmod(BOT_CONFIG_PATH, 0o600)
    ensure_legacy_path(BOT_CONFIG_PATH, LEGACY_CONFIG_PATH)
    if os.path.exists(BOT_MAIN_PATH):
        ensure_legacy_path(BOT_MAIN_PATH, LEGACY_MAIN_PATH)


def switch_to_main_bot():
    if os.path.exists(BOT_SERVICE_PATH):
        subprocess.run([BOT_SERVICE_PATH, 'restart'], check=False)
    subprocess.Popen(
        ['sh', '-c', f'sleep 1; {INSTALLER_SERVICE_PATH} stop >/dev/null 2>&1 || true'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def page_html(message='', redirect_url=None, redirect_delay_seconds=3):
    router_ip = detect_router_ip()
    notice = ''
    redirect_head = ''
    redirect_script = ''
    if message:
        notice = f'<div class="notice">{html.escape(message)}</div>'
    if redirect_url:
        escaped_redirect_url = html.escape(redirect_url, quote=True)
        redirect_head = f'<meta http-equiv="refresh" content="{redirect_delay_seconds};url={escaped_redirect_url}">'
        redirect_script = f"""
    <script>
        setTimeout(function () {{
            window.location.replace({redirect_url!r});
        }}, {redirect_delay_seconds * 1000});
    </script>"""
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Первичная настройка бота</title>
    {redirect_head}
  <style>
    :root {{ color-scheme: dark; --bg:#101418; --card:#182028; --text:#f4f7fb; --muted:#9fb0c3; --accent:#63e6be; --line:#2a3846; --warn:#ffd166; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Segoe UI, Arial, sans-serif; background:radial-gradient(circle at top, #203040, var(--bg) 60%); color:var(--text); }}
    .wrap {{ max-width:760px; margin:0 auto; padding:32px 20px 48px; }}
    .card {{ background:rgba(24,32,40,.94); border:1px solid var(--line); border-radius:18px; padding:24px; box-shadow:0 20px 60px rgba(0,0,0,.35); }}
    h1 {{ margin:0 0 12px; font-size:32px; }}
    p {{ color:var(--muted); line-height:1.5; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    label {{ display:block; font-size:14px; margin:16px 0 6px; color:var(--muted); }}
    input, select {{ width:100%; padding:12px 14px; border-radius:12px; border:1px solid var(--line); background:#0d141b; color:var(--text); }}
    .full {{ grid-column:1 / -1; }}
    button {{ margin-top:20px; width:100%; padding:14px 18px; border:0; border-radius:12px; background:var(--accent); color:#06281e; font-weight:700; cursor:pointer; }}
    .notice {{ margin:0 0 18px; padding:12px 14px; border-radius:12px; background:rgba(255,209,102,.12); color:var(--warn); border:1px solid rgba(255,209,102,.25); }}
    .hint {{ margin-top:18px; font-size:14px; color:var(--muted); }}
    @media (max-width: 680px) {{ .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:26px; }} }}
  </style>
</head>
<body>
{redirect_script}
  <div class="wrap">
    <div class="card">
      <h1>Первичная настройка бота</h1>
      <p>Эта страница запускается до основного Telegram-бота. Заполните ключи доступа, после сохранения installer запишет bot_config.py и запустит основной сервис.</p>
      {notice}
      <form method="post" action="/save">
        <div class="grid">
          <div class="full">
            <label for="token">BotFather token</label>
            <input id="token" name="token" placeholder="123456:AA..." required>
          </div>
          <div>
            <label for="username">Telegram username</label>
            <input id="username" name="username" placeholder="mylogin" required>
          </div>
          <div>
            <label for="browser_port">Порт веб-интерфейса</label>
            <input id="browser_port" name="browser_port" value="8080">
          </div>
          <div>
            <label for="appapiid">app api id</label>
            <input id="appapiid" name="appapiid" placeholder="123456" required>
          </div>
          <div>
            <label for="appapihash">app api hash</label>
            <input id="appapihash" name="appapihash" placeholder="32 hex chars" required>
          </div>
          <div>
            <label for="routerip">IP роутера</label>
            <input id="routerip" name="routerip" value="{html.escape(router_ip)}">
          </div>
          <div>
            <label for="default_proxy_mode">Режим Telegram API по умолчанию</label>
            <select id="default_proxy_mode" name="default_proxy_mode">
              <option value="none">none</option>
              <option value="shadowsocks">shadowsocks</option>
              <option value="vmess">vmess</option>
              <option value="vless">vless</option>
              <option value="trojan">trojan</option>
            </select>
          </div>
        </div>
        <button type="submit">Сохранить и запустить основной бот</button>
      </form>
      <div class="hint">После сохранения эта страница будет заменена основным интерфейсом бота на том же адресе.</div>
    </div>
  </div>
</body>
</html>
"""


class InstallerHandler(BaseHTTPRequestHandler):
    def _send_html(self, text, status=200):
        body = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send_html(page_html())

    def do_POST(self):
        if self.path != '/save':
            self._send_html(page_html('Неизвестное действие.'), status=404)
            return

        content_length = int(self.headers.get('Content-Length', '0'))
        raw_body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
        parsed = {key: values[0] for key, values in parse_qs(raw_body).items()}

        ok, message = validate_form(parsed)
        if not ok:
            self._send_html(page_html(message), status=400)
            return

        try:
            write_config(parsed)
            switch_to_main_bot()
        except Exception as exc:
            self._send_html(page_html(f'Не удалось сохранить конфиг: {exc}'), status=500)
            return

        router_ip = parsed.get('routerip', detect_router_ip()).strip() or detect_router_ip()
        browser_port = parsed.get('browser_port', str(DEFAULT_BROWSER_PORT)).strip() or str(DEFAULT_BROWSER_PORT)
        target_url = f'http://{router_ip}:{browser_port}/'
        self._send_html(
            page_html(
                f'Конфиг сохранён. Основной бот запускается. Через несколько секунд откроется основная страница: {target_url}',
                redirect_url=target_url,
            )
        )

    def log_message(self, format_text, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, DEFAULT_BROWSER_PORT), InstallerHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()