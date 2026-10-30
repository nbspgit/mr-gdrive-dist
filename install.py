#!/usr/bin/env python3
"""install.py — универсальный установщик gdrive из wheel.

Использование:
    python install.py

Установит последнюю версию wheel из GitHub Releases и настроит окружение.
Не требует git, SSH-ключей или клонирования репозитория.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# URL публичного репозитория с релизами
DIST_REPO = "nbspgit/mr-gdrive-dist"  # TODO: заменить на реальное имя
RELEASES_URL = f"https://api.github.com/repos/{DIST_REPO}/releases/latest"


def info(msg: str) -> None:
    print(f"  ✓ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠ {msg}")


def error(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


def check_python_version() -> None:
    """Проверить версию Python."""
    if sys.version_info < (3, 10):
        error(f"Python {sys.version_info.major}.{sys.version_info.minor} слишком старый. Требуется 3.10+")
    info(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def get_latest_wheel_url() -> str:
    """Получить URL последнего wheel из GitHub Releases."""
    try:
        req = urllib.request.Request(RELEASES_URL, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            release = json.loads(resp.read().decode())

        # Найти wheel-файл
        for asset in release.get("assets", []):
            if asset["name"].endswith(".whl"):
                return asset["browser_download_url"]

        error("Wheel-файл не найден в последнем релизе")
    except Exception as e:
        error(f"Не удалось получить информацию о релизе: {e}")


def download_wheel(url: str, dest: Path) -> Path:
    """Скачать wheel-файл."""
    info("Скачивание wheel...")
    try:
        urllib.request.urlretrieve(url, dest)
        info(f"Скачано: {dest.name}")
        return dest
    except Exception as e:
        error(f"Не удалось скачать wheel: {e}")


def setup_cache_dir() -> Path:
    """Настроить каталог кэша."""
    if platform.system() == "Windows":
        cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "gdrive-cache"
    else:
        cache_dir = Path.home() / "gdrive-cache"

    cache_dir.mkdir(exist_ok=True)
    os.environ["GDRIVE_CACHE_DIR"] = str(cache_dir)
    info(f"Кэш: {cache_dir}")
    return cache_dir


def install_agent_assets() -> None:
    """Установить агентские ассеты (SKILL.md)."""
    # Найти установленный пакет
    try:
        import gdrive
        package_dir = Path(gdrive.__file__).parent
    except ImportError:
        warn("Пакет gdrive не найден, пропуск агентских ассетов")
        return

    skill_src = package_dir.parent / "agent" / "skills" / "gdrive"
    if not skill_src.exists():
        warn("Агентские ассеты не найдены в пакете")
        return

    # Claude Extension / Claude Code
    if shutil.which("code"):
        result = subprocess.run(["code", "--list-extensions"], capture_output=True, text=True)
        if "anthropic" in result.stdout.lower():
            claude_skills = Path.home() / ".claude" / "skills" / "gdrive"
            claude_skills.mkdir(parents=True, exist_ok=True)
            for item in skill_src.iterdir():
                dest = claude_skills / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
            info(f"Claude: {claude_skills}")

        if "cline" in result.stdout.lower():
            cline_skills = Path.home() / ".cline" / "skills" / "gdrive"
            cline_skills.mkdir(parents=True, exist_ok=True)
            for item in skill_src.iterdir():
                dest = cline_skills / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
            info(f"Cline: {cline_skills}")


def init_drive(cache_dir: Path) -> None:
    """Инициализировать диск."""
    info("Инициализация диска...")
    try:
        subprocess.run(
            ["gdrive", "init", "0ALT1e6KliEMJUk9PVA", "--sa", "agent-orange-rw@mr-gdrive-agents.iam.gserviceaccount.com"],
            check=True,
            capture_output=True,
        )
        info("Диск инициализирован")
    except subprocess.CalledProcessError as e:
        warn(f"Не удалось инициализировать диск: {e.stderr.decode()}")
        warn("Выполните вручную: gdrive init <driveId> --sa <email>")


def login() -> None:
    """Выполнить вход."""
    info("Авторизация...")
    print()
    print("  Сейчас откроется браузер для входа в Google.")
    print("  Выберите рабочий аккаунт и подтвердите доступ.")
    print()
    try:
        subprocess.run(["gdrive", "login"], check=True)
        info("Авторизация успешна")
    except subprocess.CalledProcessError:
        warn("Не удалось выполнить вход")
        warn("Выполните вручную: gdrive login")


def main() -> None:
    print()
    print("========================================")
    print(" Установка gdrive")
    print("========================================")
    print()

    # Проверки
    check_python_version()

    # Скачать и установить wheel
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_url = get_latest_wheel_url()
        wheel_name = wheel_url.split("/")[-1]
        wheel_path = Path(tmpdir) / wheel_name
        download_wheel(wheel_url, wheel_path)
        install_wheel(wheel_path)

    # Настроить окружение
    cache_dir = setup_cache_dir()
    install_agent_assets()

    # Инициализация и вход
    init_drive(cache_dir)
    login()

    # Проверка
    print()
    print("  Проверка установки...")
    try:
        subprocess.run(["gdrive", "doctor"], check=True)
    except subprocess.CalledProcessError:
        pass

    print()
    print("========================================")
    print(" ✓ Установка завершена!")
    print("========================================")
    print()
    print(" Полезные команды:")
    print("   gdrive drives          - список доступных дисков")
    print("   gdrive find \"запрос\"   - поиск файлов")
    print("   gdrive doctor          - проверка состояния")
    print()


if __name__ == "__main__":
    main()
