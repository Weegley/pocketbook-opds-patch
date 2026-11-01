# Third-party notices / Сторонние компоненты

## Project-owned work — MIT

The root [LICENSE](LICENSE) applies to original patcher, ARM helpers, launcher/callback, shell UI/install/recovery, build/test scripts and documentation, to the extent the project author owns those contributions. There is no grant of rights to someone else's firmware, tools or pbjb. This is not an official PocketBook or pbjb release.

MIT в корне относится к собственным патчеру, ARM-обработчикам, запускателю/callback, shell UI/установке/восстановлению, сборщику, тестам и документации в пределах прав автора. Чужая прошивка, инструменты и pbjb этой лицензией не перелицензируются. Выпуск не является официальным продуктом PocketBook или pbjb.

## PocketBook firmware

No full original or modified `libopds_app_lib.so`, `opds.app`, firmware image or SDK is included in the source export or default public apps. The reader uses its own executable and supplies its own exact firmware library at runtime. The C patcher implements six guarded changes plus original helper code/table reconstruction; it is not a full library or a compressed copy of one.

Firmware rights remain with the relevant rightsholders. The project claims no permission to redistribute their binaries. Moving preparation to the user's reader, and publishing an algorithm or compact patch instead of a whole library, **does not automatically settle the legality of modification/reverse engineering or every patch-distribution question**. Review applicable rights/terms independently. No proprietary input is needed to build the public project. Optional private comparison inputs must stay outside the repository and are compared in memory.

Полные оригинальная/изменённая `libopds_app_lib.so`, `opds.app`, образ прошивки и SDK не входят в архив исходников и публичные приложения. Используются файлы самого ридера. Патчер содержит алгоритм шести проверяемых изменений, собственные ARM-обработчики и восстановление таблиц из входного файла; это не полная библиотека и не её сжатая копия.

Права на прошивку сохраняются у правообладателей; разрешение на распространение их бинарников проектом не заявляется. Подготовка на ридере и публикация алгоритма/компактного патча **сами по себе не решают все вопросы правомерности изменения, обратного анализа и распространения патчей**. Условия и права требуют самостоятельной проверки. Для сборки прошивка не нужна; частные эталоны остаются вне репозитория и сравниваются в памяти.

## ezdiy/pbjb — unchanged upstream components in Non-rooted

- Upstream: <https://github.com/ezdiy/pbjb>.
- Revision: `8f1fb889d575237f2b292e88df6aabf552142d87`.
- Authors: ezdiy and upstream contributors; see its history.
- No explicit license grant was found in this pinned snapshot or `jailbreak.c`/`su.c`; **MIT/GPL/public-domain status is not asserted**.
- Default Non-rooted embeds exact upstream `jailbreak` and `su`, obtained at build time from the pinned commit and verified by SHA-256. They are not modified or rebuilt. Their upstream sources are linked in [PBJB.md](docs/PBJB.md).
- The source export contains no binary inputs or copied pbjb source; `external/pbjb/` is ignored. `Jailbreak.app` is not needed or included. Rooted uses an existing helper without installing/removing it. Online libraries uses no root/pbjb.
- An optional `-ExternalPbjb` / `--external-pbjb` build omits those payloads and reads separately provided reader-side files instead.
- Public source availability and attribution are not presented as a specific MIT/GPL grant; this project's MIT license does not relicense pbjb.
- [PBJB.md](docs/PBJB.md) gives exact URLs and hashes. No new SSH/SMB service is installed.

В закреплённом pbjb явная лицензия не найдена; MIT/GPL/public domain ему не приписываются. Обычный Non-rooted включает неизменённые upstream `jailbreak` и `su`, полученные при сборке и проверенные по SHA. Они не перелицензируются MIT проекта. Архив исходников не содержит бинарных входов или скопированных исходников pbjb; `external/` исключён. `Jailbreak.app` не включается. Rooted и Online libraries не содержат pbjb. Необязательный вариант `-ExternalPbjb` использует отдельные файлы на ридере.

## Statically linked patcher runtime

The original patcher is compiled with Zig 0.13.0 for `arm-linux-musleabi`. Its static C runtime includes musl and compiler support. Preserve [musl copyright/license notices](licenses/musl-COPYRIGHT) and the [Zig MIT license](licenses/Zig-LICENSE). These notices are also packed inside the apps. They do not apply an MIT license to PocketBook/pbjb components.

Патчер статически собирается Zig 0.13.0 для `arm-linux-musleabi`; runtime включает musl и поддержку компилятора. Тексты прав/лицензий musl и Zig сохранены в `licenses/` и внутри приложений. Они не меняют прав на PocketBook/pbjb.

## Build/test tools and dynamic firmware dependencies

Zig is obtained separately into ignored `.tools/` from a pinned, hash-checked wheel. The wheel/upstream toolchain carries its own third-party notices. Windows tests optionally use BusyBox-w64 (GPLv2) from its official upstream; it is a local test dependency, not part of the apps/source export. Its source and notices are available at <https://frippery.org/busybox/>. Linux tests use the system's POSIX tools; none are packaged. Portable Python is downloaded into `.tools/python-runtime/`: the official CPython Windows archive and python-build-standalone Linux archive retain their upstream licenses/notices. Python distributions are not committed, source-exported or included in reader apps. URLs/hashes are in `scripts/python-bootstrap.lock`.

The source-built launcher links dynamically to the reader's existing `libstdc++.so.6`, `libgcc_s.so.1`, `libpthread.so.0`, `libc.so.6` and `libdl.so.2`. Project-owned link-only stubs record the exact ABI version references and do not supply runtime implementations. The stub DSOs never enter the app; no firmware library is required at build time. The built launcher matches the previous host SHA exactly, or the build refuses it.

Инструменты Zig/BusyBox/Python не входят в публичный экспорт. BusyBox используется только как локальная тестовая зависимость Windows. Загрузчик динамически использует существующие библиотеки ридера; собственные линковочные заглушки нужны только для записи ABI-зависимостей, не содержат прошивку и не попадают в пакет. Сборка требует побайтного совпадения загрузчика с прежним эталоном.

## inpx-web

[bookpauk/inpx-web](https://github.com/bookpauk/inpx-web) is referenced to explain catalog behavior. No server/source component is bundled, and no server modification is required.

inpx-web упомянут для описания данных OPDS; его серверные компоненты и исходники не включены, менять сервер не требуется.
