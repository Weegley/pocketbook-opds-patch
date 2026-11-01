# Автоматическая сборка

[English](BUILD.md) | **Русский**

Запустите скрипт из корня проекта. **Заранее устанавливать Python, Zig, pip, CMake или ARM-компилятор не нужно.** Прошивка, SDK и библиотека PocketBook на компьютере не требуются.

## Windows 11 x86-64

Из CMD или PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

PowerShell скачает закреплённый официальный **ZIP портативного CPython 3.14.2**, проверит SHA-256 и распакует в `.tools/python-runtime/windows-3.14.2/`. Этим интерпретатором будут подготовлены Zig/pbjb и собраны три приложения. Не используются установщик Python, реестр, постоянный PATH, права администратора, WSL и Docker.

Обычная сборка не зависит от системного Python, даже если он уже установлен. При повторных запусках используется локальный кэш. Явный расширенный вариант остаётся: `-Python C:\Path\To\python.exe` — Python 3.11+ с SSL.

## Debian/Ubuntu x86-64

```sh
sh build.sh
```

Shell скачает **CPython 3.14.2 из python-build-standalone, выпуск 20251209**, проверит SHA-256 и распакует под `.tools/python-runtime/linux-3.14.2-20251209/`. Скрипт не вызывает sudo, apt, pip и системные установщики. Системный Python не нужен. Явный расширенный вариант: `PYTHON=/path/to/python3 sh build.sh`.

Из базовой системы нужны POSIX `sh`, `uname`, `tar`, `sha256sum`, `awk`, обычные файловые утилиты и **curl либо GNU wget** с работающими HTTPS-сертификатами. Это начальные средства загрузки: без TLS-клиента shell не сможет получить архив Python. GNU wget вызывается с `--no-config --no-hsts`, чтобы не писать конфигурацию/HSTS в пользовательский профиль; чтение конфигурации curl отключено. Проект не устанавливает системные пакеты. Linux-автоподготовка рассчитана на glibc x86-64 — обычный Debian/Ubuntu, не Alpine/musl и не другие архитектуры.

## Что скачивается

Версии, URL и суммы закреплены в [python-bootstrap.lock](../scripts/python-bootstrap.lock), [dependencies.lock.json](../dependencies.lock.json) и [requirements-build.txt](../requirements-build.txt). Поиска latest нет.

| Зависимость | Источник | Локальный путь |
| --- | --- | --- |
| CPython 3.14.2 для Windows | [Официальный манифест](https://www.python.org/ftp/python/3.14.2/windows-3.14.2.json), `python-3.14.2-amd64.zip` | `.tools/downloads/`, `.tools/python-runtime/` |
| CPython 3.14.2 для Linux | [python-build-standalone 20251209](https://github.com/astral-sh/python-build-standalone/releases/tag/20251209), GNU x86-64 install-only stripped | `.tools/downloads/`, `.tools/python-runtime/` |
| Zig 0.13.0 | [Закреплённый wheel PyPI](https://pypi.org/project/ziglang/0.13.0/), без pip | `.tools/downloads/`, `.tools/python/ziglang/` |
| pbjb jailbreak/su | [Точный commit и SHA](PBJB.md) | `external/pbjb/` |
| Shell Windows, только для `-Test` | [BusyBox-w64](https://frippery.org/busybox/), закреплённый SHA | `.tools/busybox64.exe` |

URL shell Windows изменяемый: отличающийся бинарник отвергается. Если нужная версия больше не выдаётся, получите её из upstream-архива по данным `dependencies.lock.json` либо собирайте без необязательного ключа тестов. Незаметного обновления shell нет.

Python распаковывается во временный каталог и активируется только после проверки SHA архива и работоспособности интерпретатора/SSL. Прерванная загрузка или распаковка не становится активным runtime. Неожиданные суммы, перенаправленные пути инструментов и повреждённый runtime отвергаются, а не перезаписываются вслепую. При отказе предпроверки существующие `.app` не меняются.

## Результат и границы записи

- `dist/`: `Online libraries.app`, `Non-rooted patch.app`, `Rooted patch.app`, `SHA256SUMS.txt`.
- `build/`: скомпилированные собственные инструменты/линковочные заглушки, отчёты и `build.log`.
- `.cache/`: кэши компилятора, временные файлы, модели тестов; `bootstrap.log` для ошибок до запуска Python.
- `.tools/`, `external/`: скачанные и распакованные зависимости.

**Всё это остаётся внутри проекта и исключено из Git и архива исходников.** Инструменты не устанавливаются глобально и не включаются в source ZIP. PowerShell восстанавливает процессные переменные окружения после работы. Кэши компилятора/XDG/temp перенаправляются внутрь проекта, Python bytecode отключён. Linux может читать системное хранилище сертификатов, но не меняет его.

Zig собирает ARM-патчер и собственный C/C++ загрузчик. Свои линковочные объявления фиксируют ABI без библиотек прошивки на компьютере; заглушки не включаются в приложения. Загрузчик обязан совпасть с SHA universal-v8, иначе сборка остановится. Проприетарной OPDS-библиотеки нет во всех трёх `.app`. Обычный Non-rooted содержит только два точных бинарника pbjb — см. [PBJB.md](PBJB.md).

## Дополнительные режимы

```powershell
.\build.ps1 -Test             # автоматически подготовить, собрать и выполнить полный набор тестов
.\build.ps1 -Check            # только проверка, без загрузок и компиляции
.\build.ps1 -Check -Test      # также проверить зависимости тестов
.\build.ps1 -Offline          # собрать только из имеющегося кэша
.\build.ps1 -DebugBuild       # traceback в консоли при ошибке
.\build.ps1 -ExternalPbjb     # не встраивать pbjb; потребуются внешние файлы на ридере
```

```sh
sh build.sh test
sh build.sh --check
sh build.sh --offline
sh build.sh --debug
sh build.sh --external-pbjb
```

`-Setup` / `--setup` оставлен для совместимости и больше не обязателен. `-Check`/`--check` и offline-режим ничего не скачивают **даже при отсутствии Python**: выводится причина и ненулевой код. `OPDS_ZIG` явно выбирает существующий Zig 0.13.0; иначе используется локальный скачанный компилятор. `-LocalPbjb` дополнительно создаёт прежний `dist-local/`.

При ошибке консоль указывает компонент/этап и журнал. Версии/SHA не обходятся. Для ошибок сети проверьте соединение, proxy и сертификаты; проверенный закреплённый архив можно положить в `.tools/downloads/` для офлайн-распаковки. Журналы остаются внутри проекта.

## Проверка результата и тесты

```powershell
Get-FileHash -Algorithm SHA256 .\dist\*.app
Get-Content .\dist\SHA256SUMS.txt
```

```sh
(cd dist && sha256sum -c SHA256SUMS.txt)
```

Полный `-Test`/`--test` выполняет нативные модели патчера/callback, тесты сборщика, синтетические тесты подготовки Python, проверки архивов и настоящий shell-код установщика с моделями границ Linux. ARM, exploit и реальные mount на компьютере не запускаются. На Windows нужен закреплённый BusyBox; на Linux используются `/bin/sh` и обычные POSIX-команды. Полные shell-модели требуют путь проекта без пробелов; сама сборка/упаковка поддерживает пробелы. Отчёты сохраняются в `build/`.

Только быстрые проверки сборки при доступном Python: `python -B tests/test_build.py` и `python -B tests/test_bootstrap.py`. Bootstrap-тесты подменяют сеть/интерпретатор синтетическими архивами и не означают выполненную реальную Linux-автоподготовку.

Необязательное частное сравнение использует `OPDS_ORIGINAL`/`OPDS_REFERENCE` — файлы владельца **вне репозитория**. Результат сравнивается в памяти; проприетарная фикстура не записывается. Эти файлы не нужны для публичной сборки/тестов.

Упаковка tar/gzip детерминирована. Владелец подтвердил автоматическую сборку на **Windows и Linux** и работу всех трёх приложений на ридере. [VALIDATION.md](VALIDATION.md) учитывает это отдельно от проверок агента и исторических ограничений среды/сети.

## Экспорт для GitHub

Используя локальный Python — путь Windows ниже; на Linux аналогичный runtime содержит `python/bin/python3`:

```powershell
.\.tools\python-runtime\windows-3.14.2\python.exe -I -B scripts/export_source.py
.\.tools\python-runtime\windows-3.14.2\python.exe -I -B scripts/export_release.py
```

Точный список исходников — `COMMIT_FILES.txt`; source ZIP включает только эти текстовые файлы. Не добавляйте в Git `.tools/`, `.cache/`, `external/`, результаты компиляции и прошивку. ZIP выпуска содержит исходники по списку и три приложения; проприетарной библиотеки нет в обоих архивах.
