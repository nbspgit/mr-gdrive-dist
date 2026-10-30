# mr-gdrive-dist

Публичный репозиторий для распространения wheel пакета `gdrive`.

## Установка

```bash
python install.py
```

Скрипт автоматически:
- Скачает последнюю версию wheel из GitHub Releases
- Установит пакет через pip
- Настроит каталог кэша
- Установит агентские ассеты (для Claude/Cline)
- Инициализирует диск
- Выполнит авторизацию

## Обновление

```bash
pip install --upgrade https://github.com/nbspgit/mr-gdrive-dist/releases/latest/download/mr_gdrive-*.whl
```

## Безопасность

Этот репозиторий содержит только скомпилированные wheel-файлы, не исходный код.
Исходный код находится в приватном репозитории `mr_gdrive`.

При компрометации OAuth client secret:
1. Перевыпустить секрет в GCP Console
2. Обновить `DEFAULT_CLIENT_SECRET` в исходном репо
3. Пересобрать wheel и опубликовать новый релиз
4. Пользователи обновят пакет — перелогин не требуется

## Для разработчиков

Скрипт публикации wheel из приватного репо:

```bash
cd /path/to/mr_gdrive
./scripts/publish-wheel.sh
```

Это соберёт wheel, создаст GitHub Release и загрузит артефакты.
