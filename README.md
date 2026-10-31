# mr-gdrive-dist

Публичный репозиторий для распространения wheel пакета `gdrive`.
Проверенный агент: официальное расширение Claude Code (`anthropic.claude-code`).
Для других агентов: `gdrive install-assets --dest <каталог skills>` (без гарантий).

## Установка

```bash
python install.py
```

Скрипт (только стандартная библиотека Python 3.10+):
- скачивает последний релиз и проверяет sha256;
- создаёт venv (`%LOCALAPPDATA%\gdrive\venv` на Windows, `~/.local/share/gdrive/venv` на macOS);
- добавляет команду `gdrive` в PATH;
- ставит skill для Claude Code (`gdrive install-assets`);
- выполняет `gdrive login`, `gdrive init --sa`, `gdrive refresh --full`, `gdrive auth-check`.

Опции: `--skip-login`, `--skip-init`, `--version X.Y.Z`.

Доступ к Drive есть только с разрешённых IP (RDP-сервер, рабочий VPN). С других адресов
команды вернут `PERMISSION_DENIED`.

## Обновление

```bash
gdrive self-update
```

## Релизы

Каждый релиз содержит `gdrive-<версия>-py3-none-any.whl` и `gdrive-<версия>-py3-none-any.whl.sha256`.
Релиз без `.sha256` установщик и `self-update` отклоняют.

## Безопасность

Репозиторий содержит только wheel-файлы. Исходный код — в приватном репозитории `mr_gdrive`.

При компрометации OAuth client secret:
1. Перевыпустить секрет в GCP Console
2. Обновить `DEFAULT_CLIENT_SECRET` в исходном репо
3. Выпустить новый релиз (`scripts/publish-wheel.sh`)
4. Пользователи выполняют `gdrive self-update`; перелогин не требуется

## Для разработчиков

```bash
cd /path/to/mr_gdrive
pip install -e ".[dev]"
./scripts/publish-wheel.sh
```
