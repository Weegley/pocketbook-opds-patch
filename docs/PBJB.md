# pbjb provenance and build inputs / Происхождение и получение pbjb

Upstream / Проект: **<https://github.com/ezdiy/pbjb>**.

Pinned commit / Закреплённый commit: **`8f1fb889d575237f2b292e88df6aabf552142d87`**.

Default `Non-rooted patch.app` includes the following **unchanged upstream binaries**. This preserves automatic root acquisition without additional reader-side files. Rooted uses an existing compatible helper and contains no pbjb payload. Online libraries contains no pbjb and needs no root.

Обычный `Non-rooted patch.app` содержит следующие **неизменённые upstream-бинарники**. Это сохраняет автоматическое получение root без дополнительных файлов на ридере. Rooted использует существующий совместимый helper и не содержит pbjb. Online libraries не содержит pbjb и не требует root.

| File | Pinned upstream URL | SHA-256 |
| --- | --- | --- |
| `jailbreak` | [original binary](https://raw.githubusercontent.com/ezdiy/pbjb/8f1fb889d575237f2b292e88df6aabf552142d87/jailbreak) | `a523b9e77519fa0dd657268c4ad59d3ea1bcb4e07355687e6e372b68ff8c6a10` |
| `su` | [original binary](https://raw.githubusercontent.com/ezdiy/pbjb/8f1fb889d575237f2b292e88df6aabf552142d87/su) | `7babf251fc0f16dfba19c4f36305e280d5e2480b94100d1e6f16bcd564cc9fbb` |

Sources / Исходники: [jailbreak.c](https://github.com/ezdiy/pbjb/blob/8f1fb889d575237f2b292e88df6aabf552142d87/jailbreak.c), [su.c](https://github.com/ezdiy/pbjb/blob/8f1fb889d575237f2b292e88df6aabf552142d87/su.c).

Credit belongs to ezdiy and the upstream contributors. No explicit license grant was found in the pinned snapshot, so this project does not label pbjb MIT, GPL or public domain. The project's MIT license applies to original project code, not pbjb. Public source availability is not represented here as a particular license grant. See [third-party notices](../THIRD_PARTY_NOTICES.md).

Авторство принадлежит ezdiy и участникам upstream. В закреплённом снимке явная лицензия не найдена, поэтому проект не обозначает pbjb как MIT, GPL или public domain. MIT собственного проекта не перелицензирует pbjb. Доступность исходников не представляется здесь как конкретное лицензионное разрешение. См. [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Build-time acquisition

An ordinary `build.ps1` / `sh build.sh` run obtains missing components from these exact commit-pinned URLs, checks SHA-256 and stores them only in ignored `external/pbjb/`. `-Setup`/`--setup` remains an alias. No latest-release lookup is used. Rebuilding offline uses those verified local files.

Separate commands:

```powershell
python -B scripts/get_pbjb.py --download
# Or validate/import files from your own upstream checkout:
python -B scripts/get_pbjb.py --from PATH_TO_UPSTREAM_COPY
.\build.ps1
```

```sh
python3 -B scripts/get_pbjb.py --download
sh build.sh
```

The downloader never runs these binaries. The builder validates them again before packaging. Only `Non-rooted patch.app` receives `pbjb/jailbreak` and `pbjb/su`. `Jailbreak.app` is unnecessary: our original UI invokes the upstream `jailbreak [cmd]` CLI directly. No third-party binary is manually edited or rebuilt and then presented as the pinned input. The runtime verifies executable copies again before use. No SSH/SMB service is installed.

`external/` is not committed or exported as source. Generated `.app` files are release artifacts in `dist/`, not hidden inputs to the build. All three apps exclude the PocketBook library; they create it from the reader's original at runtime.

## Получение при сборке

Обычный запуск `build.ps1` / `sh build.sh` получает отсутствующие файлы по точным URL указанного commit, проверяет SHA-256 и сохраняет только в исключённую из Git папку `external/pbjb/`. `-Setup`/`--setup` оставлен для совместимости. Поиск latest не выполняется. Для офлайн-сборки используются эти проверенные локальные входы.

Отдельная команда `python -B scripts/get_pbjb.py --download` получает файлы; `--from ПУТЬ` проверяет и импортирует их из вашей upstream-копии. Скрипт их не исполняет. Сборщик повторно проверяет SHA перед упаковкой. Только Non-rooted получает два файла `pbjb/jailbreak` и `pbjb/su`. `Jailbreak.app` не нужен: собственный интерфейс напрямую вызывает `jailbreak [cmd]`. Чужие бинарники не редактируются и не пересобираются под видом исходных. Перед исполнением на ридере копии проверяются ещё раз. SSH/SMB не устанавливаются.

`external/` не попадает в Git/архив исходников. Готовые `.app` — результаты в `dist/`, а не скрытые входы сборщика. Во всех трёх отсутствует библиотека PocketBook: она создаётся на ридере из его оригинала.

## Optional external-components variant / Необязательный внешний вариант

Build with `.\build.ps1 -ExternalPbjb` or `sh build.sh --external-pbjb` to omit pbjb even from Non-rooted. No pbjb input is needed for that build. When root is absent, place the two verified files on the reader at:

```text
system/opds-pbjb/8f1fb889d575237f2b292e88df6aabf552142d87/jailbreak
system/opds-pbjb/8f1fb889d575237f2b292e88df6aabf552142d87/su
```

This external mode refuses missing/wrong files. The reader downloads nothing. A self-contained root acquisition without either the executables or a compatible installed helper is not possible with this mechanism.

Ключ `-ExternalPbjb` / `--external-pbjb` исключает pbjb и из Non-rooted; для такой сборки входы pbjb не нужны. Если root отсутствует, пользователь кладёт два проверенных файла на ридер по путям выше. При отсутствии/ошибке SHA — отказ, без скачивания и без попыток угадать версию. Автономное получение root этим механизмом невозможно без его исполняемых файлов либо уже установленного совместимого helper.

## Existing root / Уже установленный root

Rooted requires supported `/mnt/secure/su`, SHA above, owner/group `0:0`, mode `4755`; calling it as `sreader` must obtain UID 0. It does not install, change or remove root. Non-rooted can use the same existing helper, but asks an additional explicit confirmation before scheduling its deletion after success. Cancel and use Rooted if you want to keep it. Foreign helper/symlink/unsafe metadata is refused. Failures may intentionally leave recovery root available.

Rooted требует поддерживаемый `/mnt/secure/su` с указанным SHA, владельцем/группой `0:0`, режимом `4755` и проверяемым получением UID 0 от `sreader`. Он не устанавливает, не меняет и не удаляет root. Non-rooted использует тот же helper, но перед подготовкой удаления ранее установленного root требует дополнительного явного подтверждения. Для сохранения root отмените действие и используйте Rooted. Чужие helper, ссылки и небезопасные права отвергаются. При ошибке root может остаться для восстановления.
