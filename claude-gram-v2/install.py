#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Claude-Gram v2 Python Installer
# Fork: claude-gram by tg: @justidev, orig by @ripcats

import os
import sys
import re
import shutil
import subprocess
from pathlib import Path

# Включение ANSI цветов на Windows
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# Цветовая палитра
CLR_RESET = "\x1b[0m"
CLR_GREEN = "\x1b[38;2;0;255;128m"
CLR_YELLOW = "\x1b[38;2;255;220;0m"
CLR_RED = "\x1b[38;2;255;64;64m"
CLR_CYAN = "\x1b[38;2;0;220;255m"

# Генератор трехцветного градиента Claude (оранжевый-белый-красный)
def gradient_text(text, start_rgb=(235, 94, 40), mid_rgb=(255, 255, 255), end_rgb=(185, 28, 28)):
    lines = text.splitlines()
    gradient_lines = []
    for line in lines:
        n = len(line)
        if n == 0:
            gradient_lines.append("")
            continue
        line_colored = []
        for i, char in enumerate(line):
            if i < n / 2:
                factor = i / (n / 2)
                r = int(start_rgb[0] + (mid_rgb[0] - start_rgb[0]) * factor)
                g = int(start_rgb[1] + (mid_rgb[1] - start_rgb[1]) * factor)
                b = int(start_rgb[2] + (mid_rgb[2] - start_rgb[2]) * factor)
            else:
                factor = (i - n / 2) / (n / 2)
                r = int(mid_rgb[0] + (end_rgb[0] - mid_rgb[0]) * factor)
                g = int(mid_rgb[1] + (end_rgb[1] - mid_rgb[1]) * factor)
                b = int(mid_rgb[2] + (end_rgb[2] - mid_rgb[2]) * factor)
            line_colored.append(f"\x1b[38;2;{r};{g};{b}m{char}")
        line_colored.append(CLR_RESET)
        gradient_lines.append("".join(line_colored))
    return "\n".join(gradient_lines)

ASCII_ART = r"""
 _____ _                 _          ____                     
/  ___| |               | |        / ___|                    
| |   | | __ _ _   _  __| | ___   | |  _ _ __ __ _ _ __ ___  
| |   | |/ _` | | | |/ _` |/ _ \  | | |_| '__/ _` | '_ ` _ \ 
| |___| | (_| | |_| | (_| |  __/  | |__| | | | (_| | | | | | |
\_____|_|\__,_|\__,_|\__,_|\___|   \____|_|_|  \__,_|_| |_| |_| v2
"""

def print_banner():
    os.system('cls' if sys.platform == 'win32' else 'clear')
    cols = shutil.get_terminal_size().columns
    if cols >= 65:
        print(gradient_text(ASCII_ART))
        width = 65
    else:
        print(gradient_text("  === Claude-Gram v2 ==="))
        width = 40

    print(gradient_text("  " + "=" * (width - 4)))
    print(f"  {CLR_GREEN}Claude-Gram v2 – Автоматический инсталлятор бота и MCP канала{CLR_RESET}")
    print(f"  {CLR_CYAN}Разработчик (Оригинал): @ripcats | Автор форка: tg @justidev{CLR_RESET}")
    print(gradient_text("  " + "=" * (width - 4)))
    print()

def print_claudgramik():
    esc = "\x1b"
    c_orange = f"{esc}[38;2;235;94;40m"
    c_reset = CLR_RESET
    c_cyan = CLR_CYAN
    
    print(f"  {c_orange}  ████████████  {c_reset}    Привет! Я Клодграмик.")
    print(f"  {c_orange}  ██  ████  ██  {c_reset}    – Начнём настройку {c_cyan}Claude-Gram v2{c_reset}?")
    print(f"  {c_orange}████████████████{c_reset}")
    print(f"  {c_orange}  ████████████  {c_reset}")
    print(f"  {c_orange}  ██ ██  ██ ██  {c_reset}")
    print()

def main():
    print_banner()
    print_claudgramik()
    
    # 1. Интерактивный опрос
    print(f"{CLR_CYAN}[1/5] Настройка Telegram конфигурации:{CLR_RESET}")
    
    while True:
        bot_token = input(f"🔑 {CLR_YELLOW}Введите Telegram Bot Token:{CLR_RESET} ").strip()
        if re.match(r"^[0-9]+:[a-zA-Z0-9_-]+$", bot_token):
            break
        print(f"{CLR_RED}❌ Неверный формат токена! Пример: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ{CLR_RESET}")

    while True:
        owner_id = input(f"👤 {CLR_YELLOW}Введите Ваш Telegram ID (только цифры):{CLR_RESET} ").strip()
        if re.match(r"^[0-9]+$", owner_id):
            break
        print(f"{CLR_RED}❌ ID должен состоять только из цифр!{CLR_RESET}")
        
    print()

    # 2. Установка pip-пакетов
    print(f"{CLR_CYAN}[2/5] Установка зависимостей Python...{CLR_RESET}")
    
    # Пытаемся обновить pip, но не падаем при неудаче
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--break-system-packages"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Умная установка пакетов с поддержкой --break-system-packages
    packages = ["aiogram", "orjson", "curl_cffi", "playwright"]
    installed = False
    
    try:
        # Пробуем установить с флагом --break-system-packages (для Debian/Ubuntu PEP 668)
        subprocess.run([sys.executable, "-m", "pip", "install"] + packages + ["--break-system-packages"], check=True)
        installed = True
    except subprocess.CalledProcessError:
        pass

    if not installed:
        try:
            # Если не вышло (например, старый pip), пробуем без флага
            subprocess.run([sys.executable, "-m", "pip", "install"] + packages, check=True)
        except Exception as e:
            print(f"{CLR_RED}❌ Ошибка при установке зависимостей: {e}{CLR_RESET}")
            sys.exit(1)

    # Инициализация playwright
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"{CLR_RED}❌ Ошибка при установке браузера Playwright: {e}{CLR_RESET}")
        sys.exit(1)

    # Пути
    INSTALL_DIR = Path(__file__).parent.resolve()
    HOME_DIR = Path.home()
    STATE_DIR = HOME_DIR / ".claude" / "channels" / "telegram"
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Запись настроек
    (STATE_DIR / ".env").write_text(f"TELEGRAM_BOT_TOKEN={bot_token}\n", encoding="utf-8")
    (STATE_DIR / "access.json").write_text(f'{{"allowFrom": ["{owner_id}"]}}\n', encoding="utf-8")
    print(f"{CLR_GREEN}✅ Конфигурация успешно сохранена в {STATE_DIR}{CLR_RESET}")

    # 3. Создание обертки запуска
    print(f"\n{CLR_CYAN}[3/5] Создание обертки запуска бота...{CLR_RESET}")
    
    wrapper_code = r"""#!/usr/bin/env python3
import json
import os
import re
import select
import sys
import time
import urllib.request
import signal
from pathlib import Path

STATE_DIR = Path("##HOME##/.claude/channels/telegram")
ACTIVE_CLI_FILE = STATE_DIR / "active_cli"
LOG_FILE_PATH = STATE_DIR / "bot.log"

def get_active_cli() -> str:
    if ACTIVE_CLI_FILE.exists():
        return ACTIVE_CLI_FILE.read_text("utf-8").strip()
    return "claude"

def send_telegram_alert(text: str) -> None:
    try:
        access_path = STATE_DIR / "access.json"
        if not access_path.exists():
            return
        access = json.loads(access_path.read_text("utf-8"))
        if not access.get("allowFrom"):
            return
        chat_id = access["allowFrom"][0]

        thread_path = STATE_DIR / "session_thread_id"
        thread_id = None
        if thread_path.exists():
            val = thread_path.read_text("utf-8").strip()
            if val and val != "None":
                thread_id = int(val)

        env_path = STATE_DIR / ".env"
        token = None
        if env_path.exists():
            for line in env_path.read_text("utf-8").splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
        if not token:
            return

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if thread_id is not None:
            payload["message_thread_id"] = thread_id

        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
    except Exception as e:
        sys.stderr.write(f"Failed to send Telegram alert: {e}\n")

def get_active_session_id() -> str:
    active_sess_file = Path("##HOME##/.claude/channels/telegram/active_session_id")
    if active_sess_file.exists():
        try:
            val = active_sess_file.read_text("utf-8").strip()
            if val and val != "new":
                return val
            return ""
        except Exception:
            pass
    project_dir = Path("##HOME##/.claude/projects/-root")
    if project_dir.exists():
        try:
            files = list(project_dir.glob("*.jsonl"))
            if files:
                files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                return files[0].stem
        except Exception:
            pass
    return ""

def main() -> int:
    cli = get_active_cli()
    if cli == "agy" or not Path("##HOME##/.claude/.credentials.json").exists():
        sys.stderr.write("No active credentials found. Running server.py standalone...\n")
        cmd = ["python3" if sys.platform != "win32" else sys.executable, "##INSTALL_DIR##/server.py"]
        os.execvp(cmd[0], cmd)
        return 0

    cmd = ["claude", "--channels", "plugin:claude-gram@ripcats-marketplace"]
    try:
        settings_path = Path("##HOME##/.claude/settings.json")
        if settings_path.exists():
            model_val = json.loads(settings_path.read_text("utf-8")).get("model")
            if model_val:
                cmd.extend(["--model", model_val])
    except Exception:
        pass
    active_sess = get_active_session_id()
    if active_sess:
        session_file = Path(f"##HOME##/.claude/projects/-root/{active_sess}.jsonl")
        if session_file.exists() and session_file.stat().st_size > 0:
            cmd.extend(["--resume", active_sess])
        else:
            cmd.extend(["--session-id", active_sess])
    else:
        cmd.append("-c")

    if sys.platform == "win32":
        # Windows PTY is not supported, run server.py standalone as fallback in wrapper
        sys.stderr.write("Running Claude-Gram server.py standalone on Windows...\n")
        cmd = [sys.executable, "##INSTALL_DIR##/server.py"]
        os.execvp(sys.executable, cmd)
        return 0

    claude_bin = "/usr/bin/claude"
    pid, fd = os.forkpty()
    if pid == 0:
        os.execvp(claude_bin, cmd)
        os._exit(127)

    def sig_handler(signum, frame):
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        sys.exit(143 if signum == signal.SIGTERM else 130)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    pty_buffer = ""
    last_alert_time = 0.0
    auth_failed = False

    log_file = None
    try:
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(LOG_FILE_PATH, "a", encoding="utf-8")
    except Exception:
        pass

    while True:
        try:
            r, _, _ = select.select([fd], [], [], 1.0)
        except (OSError, ValueError):
            break
        if fd in r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break

            decoded = data.decode("utf-8", errors="ignore")
            sys.stdout.write(decoded)
            sys.stdout.flush()
            if log_file:
                try:
                    log_file.write(decoded)
                    log_file.flush()
                except Exception:
                    pass
            clean_data = ansi_escape.sub("", decoded)
            pty_buffer += clean_data
            if len(pty_buffer) > 10000:
                pty_buffer = pty_buffer[-10000:]

            now = time.time()
            if now - last_alert_time > 15.0:
                matched_alert = None
                lower_buf = pty_buffer.lower()

                if "ratelimiterror" in lower_buf or "rate limit reached" in lower_buf or "rate limit exceeded" in lower_buf:
                    matched_alert = "⚠️ <b>Claude Code: Превышен лимит запросов (Rate Limit).</b> Пожалуйста, подождите."
                elif "overloadederror" in lower_buf or ("overloaded" in lower_buf and "error" in lower_buf):
                    matched_alert = "⚠️ <b>Claude Code: Серверы Anthropic перегружены (Overloaded).</b> Пожалуйста, повторите попытку."
                elif "billing limit" in lower_buf:
                    matched_alert = "⚠️ <b>Claude Code: Достигнут лимит оплаты (Billing Limit).</b>"
                elif "credit balance too low" in lower_buf or "insufficient credit" in lower_buf or "insufficient funds" in lower_buf:
                    matched_alert = "⚠️ <b>Claude Code: Недостаточно средств на балансе API.</b>"
                elif "invalid authentication credentials" in lower_buf or "api error: 401" in lower_buf or "please run /login" in lower_buf:
                    matched_alert = "⚠️ <b>Сессия устарела или недействительна.</b> Пожалуйста, выполните повторную авторизацию с помощью команды /login."
                    auth_failed = True

                if matched_alert:
                    send_telegram_alert(matched_alert)
                    last_alert_time = now
                    for keyword in ["ratelimiterror", "rate limit reached", "rate limit exceeded", 
                                    "overloadederror", "overloaded", "billing limit", 
                                    "credit balance too low", "insufficient credit", "insufficient funds",
                                    "invalid authentication credentials", "api error: 401", "please run /login"]:
                        pty_buffer = re.sub(re.escape(keyword), f"[processed_{keyword}]", pty_buffer, flags=re.IGNORECASE)

    _, status = os.waitpid(pid, 0)
    if auth_failed:
        time.sleep(30)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    return 1

if __name__ == "__main__":
    sys.exit(main())
"""

    wrapper_code = wrapper_code.replace("##HOME##", str(HOME_DIR).replace("\\", "\\\\"))
    wrapper_code = wrapper_code.replace("##INSTALL_DIR##", str(INSTALL_DIR).replace("\\", "\\\\"))

    if sys.platform == "win32":
        WRAPPER_PATH = STATE_DIR / "claude-telegram-bot.py"
        WRAPPER_PATH.write_text(wrapper_code, encoding="utf-8")
        
        BAT_PATH = STATE_DIR / "start-bot.bat"
        BAT_PATH.write_text(f'@echo off\n"{sys.executable}" "{WRAPPER_PATH}"\n', encoding="utf-8")
        print(f"{CLR_GREEN}✅ Скрипты запуска успешно созданы в {STATE_DIR}{CLR_RESET}")
    else:
        WRAPPER_PATH = Path("/usr/local/bin/claude-telegram-bot")
        try:
            temp_file = Path("/tmp/claude-telegram-bot.tmp")
            temp_file.write_text(wrapper_code, encoding="utf-8")
            
            if os.access("/usr/local/bin", os.W_OK):
                shutil.move(str(temp_file), str(WRAPPER_PATH))
                WRAPPER_PATH.chmod(0o755)
            else:
                subprocess.run(["sudo", "mv", str(temp_file), str(WRAPPER_PATH)], check=True)
                subprocess.run(["sudo", "chmod", "755", str(WRAPPER_PATH)], check=True)
            print(f"{CLR_GREEN}✅ Обертка запуска успешно установлена в {WRAPPER_PATH}{CLR_RESET}")
        except Exception as e:
            print(f"{CLR_RED}❌ Ошибка создания запускаемой обертки: {e}{CLR_RESET}")

    # 4. Настройка автозапуска / службы
    print(f"\n{CLR_CYAN}[4/5] Настройка фоновой службы автозапуска...{CLR_RESET}")
    
    if sys.platform == "win32":
        # Настройка планировщика задач Windows
        task_name = "ClaudeGramBot"
        cmd = ["schtasks", "/Create", "/TN", task_name, "/TR", f'cmd.exe /c "{BAT_PATH}"', "/SC", "ONLOGON", "/F"]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"{CLR_GREEN}✅ Задача '{task_name}' успешно зарегистрирована в Планировщике задач Windows!{CLR_RESET}")
        except Exception:
            # Альтернатива: Автозагрузка
            startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            try:
                # Создаем vbs скрипт для скрытого запуска
                vbs_path = startup_dir / "Claude-Gram.vbs"
                vbs_path.write_text(f'CreateObject("Wscript.Shell").Run "cmd.exe /c {BAT_PATH}", 0, True', encoding="utf-8")
                print(f"{CLR_GREEN}✅ Скрипт запуска добавлен в папку автозагрузки Windows.{CLR_RESET}")
            except Exception as e:
                print(f"{CLR_RED}❌ Не удалось настроить автозапуск: {e}{CLR_RESET}")

    elif sys.platform == "darwin":
        # launchd на macOS
        plist_path = HOME_DIR / "Library" / "LaunchAgents" / "me.ripcats.claude-telegram.plist"
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>me.ripcats.claude-telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>{WRAPPER_PATH}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>{HOME_DIR}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
"""
        try:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_path.write_text(plist_content, encoding="utf-8")
            subprocess.run(["launchctl", "unload", str(plist_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["launchctl", "load", "-w", str(plist_path)], check=True)
            print(f"{CLR_GREEN}✅ launchd агент успешно запущен в macOS!{CLR_RESET}")
        except Exception as e:
            print(f"{CLR_RED}❌ Не удалось настроить launchd агент: {e}{CLR_RESET}")

    else:
        # systemd в Linux
        if Path("/run/systemd/system").exists() and shutil.which("systemctl"):
            service_content = f"""[Unit]
Description=Claude Code Telegram channel (always-on)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={os.getlogin() if hasattr(os, "getlogin") else "root"}
WorkingDirectory={HOME_DIR}
Environment=HOME={HOME_DIR}
Environment=CLAUDE_ALLOW_ROOT=1
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart={WRAPPER_PATH}
Restart=always
RestartSec=5
TimeoutStopSec=20
KillMode=control-group

[Install]
WantedBy=multi-user.target
"""
            service_file = Path("/etc/systemd/system/claude-telegram.service")
            try:
                temp_service = Path("/tmp/claude-telegram.service.tmp")
                temp_service.write_text(service_content, encoding="utf-8")
                
                subprocess.run(["sudo", "mv", str(temp_service), str(service_file)], check=True)
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(["sudo", "systemctl", "enable", "claude-telegram.service"], check=True)
                subprocess.run(["sudo", "systemctl", "restart", "claude-telegram.service"], check=True)
                print(f"{CLR_GREEN}✅ systemd служба claude-telegram успешно запущена!{CLR_RESET}")
            except Exception as e:
                print(f"{CLR_RED}❌ Ошибка при настройке systemd службы: {e}{CLR_RESET}")
        elif shutil.which("pm2"):
            try:
                subprocess.run(["pm2", "delete", "claude-telegram"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pm2", "start", str(WRAPPER_PATH), "--name", "claude-telegram", "--update-env"], check=True)
                subprocess.run(["pm2", "save"], check=True)
                print(f"{CLR_GREEN}✅ Бот успешно зарегистрирован в PM2!{CLR_RESET}")
            except Exception as e:
                print(f"{CLR_RED}❌ Ошибка при регистрации в PM2: {e}{CLR_RESET}")
        else:
            # Fallback: nohup
            run_script = STATE_DIR / "run_daemon.sh"
            daemon_content = f"""#!/usr/bin/env bash
while true; do
    echo "[$(date)] Starting Claude-Gram bot..." >> "{STATE_DIR}/daemon.log"
    {WRAPPER_PATH} >> "{STATE_DIR}/daemon.log" 2>&1
    sleep 5
done
"""
            try:
                run_script.write_text(daemon_content, encoding="utf-8")
                run_script.chmod(0o755)
                subprocess.Popen(["nohup", str(run_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                print(f"{CLR_GREEN}✅ Бот запущен в фоновом режиме через nohup (лог в {STATE_DIR}/daemon.log){CLR_RESET}")
            except Exception as e:
                print(f"{CLR_RED}❌ Не удалось настроить запуск через nohup: {e}{CLR_RESET}")

    # 5. Завершение
    print()
    print(gradient_text("  ========================================================================="))
    print(f"  🎉 {CLR_GREEN}Установка Claude-Gram v2 успешно завершена!{CLR_RESET}")
    print(f"  👤 Владелец: ID {CLR_CYAN}{owner_id}{CLR_RESET}")
    print(f"  👉 Отправьте боту команду {CLR_YELLOW}/start{CLR_RESET} в Telegram для начала работы.")
    print(gradient_text("  ========================================================================="))
    print()

if __name__ == "__main__":
    main()
