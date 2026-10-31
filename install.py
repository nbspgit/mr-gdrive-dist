#!/usr/bin/env python3
"""install.py — единственный установщик gdrive (D19).

    python install.py [--skip-login] [--skip-init] [--version X.Y.Z]

Шаги: wheel из GitHub Releases (с проверкой sha256) → venv в фиксированном каталоге →
команда `gdrive` в PATH → skill для Claude Code → login → init --sa → refresh --full →
auth-check.

Не требует git, SSH-ключей и прав администратора. Только стандартная библиотека.
Поддерживается официальное расширение Claude Code (`anthropic.claude-code`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
import venv
from pathlib import Path

DIST_REPO = "nbspgit/mr-gdrive-dist"
RELEASES_API = f"https://api.github.com/repos/{DIST_REPO}/releases"

# Параметры рабочего диска (docs/30, docs/80)
DRIVE_ID = "0ALT1e6KliEMJUk9PVA"
SERVICE_ACCOUNT = "agent-orange-rw@mr-gdrive-agents.iam.gserviceaccount.com"

IS_WINDOWS = platform.system() == "Windows"


def info(msg: str) -> None:
    print(f"  ✓ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠ {msg}")


def fail(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def _reconfigure_stdout() -> None:
    """Кириллица и ✓ в консолях cp1251/cp866 не должны ронять установщик."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


# ---------------------------------------------------------------------------
# Пути
# ---------------------------------------------------------------------------


def install_root() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "gdrive"
    return Path.home() / ".local" / "share" / "gdrive"


def venv_dir() -> Path:
    return install_root() / "venv"


def venv_python() -> Path:
    return venv_dir() / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def venv_gdrive() -> Path:
    return venv_dir() / ("Scripts/gdrive.exe" if IS_WINDOWS else "bin/gdrive")


# ---------------------------------------------------------------------------
# Релиз и wheel
# ---------------------------------------------------------------------------


def _get(url: str, accept: str | None = None) -> bytes:
    headers = {"User-Agent": "gdrive-installer"}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_release(version: str | None) -> dict:
    url = f"{RELEASES_API}/tags/v{version}" if version else f"{RELEASES_API}/latest"
    try:
        return json.loads(_get(url, "application/vnd.github+json").decode())
    except Exception as e:
        fail(f"Не удалось получить информацию о релизе ({url}): {e}")
        raise  # недостижимо


def download_verified_wheel(release: dict, dest_dir: Path) -> Path:
    assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    wheel_name = next((n for n in assets if n.endswith(".whl")), None)
    if wheel_name is None:
        fail("В релизе нет wheel-файла")
    sha_url = assets.get(f"{wheel_name}.sha256")
    if sha_url is None:
        fail(f"В релизе нет {wheel_name}.sha256 — установка отклонена")

    expected = _get(sha_url).decode().split()[0].lower()
    data = _get(assets[wheel_name])
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        fail(f"sha256 не совпадает (ожидалось {expected}, получено {actual})")

    path = dest_dir / wheel_name
    path.write_bytes(data)
    info(f"Скачан и проверен: {wheel_name}")
    return path


# ---------------------------------------------------------------------------
# venv и PATH
# ---------------------------------------------------------------------------


def create_venv_and_install(wheel: Path) -> None:
    vdir = venv_dir()
    if not venv_python().exists():
        vdir.parent.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(vdir)
        info(f"Создан venv: {vdir}")
    else:
        info(f"Используется существующий venv: {vdir}")
    proc = subprocess.run(
        [
            str(venv_python()), "-m", "pip", "install", "--upgrade", "--force-reinstall",
            "--disable-pip-version-check", str(wheel),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(f"pip install не удался:\n{proc.stderr[-2000:]}")
    if not venv_gdrive().exists():
        fail(f"После установки не найден {venv_gdrive()}")
    info("Пакет gdrive установлен")


def _on_path(directory: Path) -> bool:
    parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    norm = os.path.normcase(os.path.normpath(str(directory)))
    return any(os.path.normcase(os.path.normpath(p)) == norm for p in parts)


def add_windows_user_path(directory: Path) -> None:
    """Добавить каталог в ПОЛЬЗОВАТЕЛЬСКИЙ PATH через реестр (без setx и усечения)."""
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE
    ) as key:
        try:
            current, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, kind = "", winreg.REG_EXPAND_SZ
        entries = [e for e in current.split(";") if e]
        norm = os.path.normcase(os.path.normpath(str(directory)))
        if any(os.path.normcase(os.path.normpath(e)) == norm for e in entries):
            return
        entries.append(str(directory))
        winreg.SetValueEx(key, "Path", 0, kind, ";".join(entries))
    info(f"Добавлено в пользовательский PATH: {directory} (откройте новый терминал)")


def ensure_on_path() -> None:
    if IS_WINDOWS:
        scripts = venv_gdrive().parent
        if not _on_path(scripts):
            add_windows_user_path(scripts)
        return
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    link = bin_dir / "gdrive"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(venv_gdrive())
    info(f"Ссылка: {link} → {venv_gdrive()}")
    if not _on_path(bin_dir):
        warn(f'{bin_dir} не в PATH. Добавьте в ~/.zshrc:  export PATH="$HOME/.local/bin:$PATH"')



# ---------------------------------------------------------------------------
# Шаги gdrive
# ---------------------------------------------------------------------------


def run_gdrive(*args: str) -> int:
    """Запуск gdrive по абсолютному пути (PATH в этой сессии ещё может не обновиться)."""
    try:
        return subprocess.run([str(venv_gdrive()), *args]).returncode
    except OSError as e:
        warn(f"Не удалось запустить gdrive {' '.join(args)}: {e}")
        return 70


def post_install(skip_login: bool, skip_init: bool) -> int:
    print()
    print("  Установка skill для Claude Code...")
    run_gdrive("install-assets")

    init_cmd = f"gdrive init {DRIVE_ID} --sa {SERVICE_ACCOUNT}"
    if skip_login:
        warn("Пропущены login/init/refresh (--skip-login). Выполните вручную:")
        print("      gdrive login")
        print(f"      {init_cmd}")
        print("      gdrive refresh --full")
        return 0

    print()
    print("  Сейчас откроется браузер для входа в Google.")
    print("  Выберите рабочий аккаунт и подтвердите доступ.")
    if run_gdrive("login") != 0:
        warn("Вход не выполнен. Повторите: gdrive login (нужен браузер на этой машине)")
        return 4

    if not skip_init:
        rc = run_gdrive("init", DRIVE_ID, "--sa", SERVICE_ACCOUNT)
        if rc != 0:
            warn(f"init не выполнен; повторите: {init_cmd}")
            return rc

    print()
    print("  Первичная индексация диска...")
    refresh_rc = run_gdrive("refresh", "--full")
    if refresh_rc != 0:
        warn("refresh --full не удался (см. сообщение выше)")

    print()
    print("  Проверка авторизации...")
    auth_rc = run_gdrive("auth-check")
    if 5 in (auth_rc, refresh_rc):
        print()
        warn("PERMISSION_DENIED: вероятно, этот IP вне разрешённого периметра VPC-SC.")
        print("      Подключитесь через RDP-сервер или рабочий VPN и повторите:")
        print("      gdrive auth-check")
    return auth_rc or refresh_rc


def main() -> None:
    _reconfigure_stdout()
    ap = argparse.ArgumentParser(description="Установка gdrive")
    ap.add_argument("--skip-login", action="store_true", help="только установить, без входа")
    ap.add_argument("--skip-init", action="store_true", help="не выполнять gdrive init")
    ap.add_argument("--version", help="конкретная версия (по умолчанию — последняя)")
    args = ap.parse_args()

    print()
    print("========================================")
    print(" Установка gdrive")
    print("========================================")
    print()

    if sys.version_info < (3, 10):
        fail(f"Python {platform.python_version()} слишком старый. Нужен 3.10+")
    info(f"Python {platform.python_version()} ({platform.system()})")

    release = fetch_release(args.version)
    with tempfile.TemporaryDirectory() as tmp:
        wheel = download_verified_wheel(release, Path(tmp))
        create_venv_and_install(wheel)

    ensure_on_path()
    rc = post_install(args.skip_login, args.skip_init)

    print()
    print("========================================")
    print(" ✓ Установка завершена" if rc == 0 else " ⚠ Установка завершена с замечаниями")
    print("========================================")
    print()
    print(' Дальше:  gdrive find "запрос"   |   gdrive doctor   |   gdrive self-update')
    print()
    sys.exit(0 if rc == 0 else rc)


if __name__ == "__main__":
    main()

