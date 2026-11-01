# Exact patch specification / Точная спецификация

Target: PocketBook 632 / U632.6.11.2001, ELF32 little-endian ARM EABI. Source size **598364**, source SHA `e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98`. Result size **610748**, SHA `c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5`.

The algorithm is [patcher.c](../../src/patcher/patcher.c). The original assembly is [navigation-subtitle.s](navigation-subtitle.s); the build assembles it and the tests compare all instruction bytes against the C word array. [reference.json](reference.json) records the historical offsets/expected-byte guards. Its old experimental status refers to the original research phase, not to a new runtime device test.

## Transformation

Addresses marked **file offset** refer to bytes on disk. Addresses marked **RVA** are module-relative virtual addresses, not absolute runtime addresses. In the appended segment only, file offset equals RVA by design.

| Original file offset | Change | Purpose |
| --- | --- | --- |
| `0x1c` | ELF `e_phoff` → `0x93000` | Relocate program-header table into a mapped segment |
| `0x20` | ELF `e_shoff` → `0x94d84` | Relocate/extend section headers |
| `0x2c` | ELF `e_phnum` 6 → 7 | Add one load segment |
| `0x30` | ELF `e_shnum` 26 → 27 | Add `.opds_patch` section |
| `0x3d41c` | `cmp r6,#0` → `bl` RVA `0x930e0` | Allow the second-line layout for text Content in navigation entries while preserving native entry classification |
| `0x3d558` | Two loads → `bl` RVA `0x93140` + ARM NOP | Select navigation Content text/control block, retaining native acquisition author handling |

The output starts with an exact copy of the original file. Only those six sites are overwritten. The appended area is zero-initialized; no original appended firmware data is shipped in the patcher.

1. Program headers are read from the user's input, copied, and the `PT_ARM_EXIDX` header is updated. A seventh header describes a page-aligned **RX**, not RWX, `PT_LOAD` at offset/RVA `0x93000`. Existing loaded segments, GNU_STACK, RELRO, imports and symbol tables remain unchanged.
2. Two original ARM helpers occupy RVA `0x930e0` (96 bytes) and `0x93140` (36 bytes). They validate the native `text` content type and select its text, without changing `r6` entry classification or the folder → book → details flow.
3. `.ARM.exidx` is relocated from data in the user's ELF to RVA `0x93164`. PREL31 function and external unwind-table pointers are decoded at their old addresses and re-encoded at their new addresses. Inline unwind words remain unchanged. Two helper entries plus a terminating entry are added. This avoids breaking exception/unwind handling.
4. The user's section-name string table is copied and extended only with `.opds_patch\0`. Section headers are copied and corrected for relocated exidx/names, then an executable/allocated patch section is added.
5. The complete result is SHA-256-verified **before any output file is created**. Unknown original size/hash, wrong model/firmware arguments, unexpected ELF boundaries/hooks and any different result are refused. Output creation is exclusive: an existing file or symbolic link is never overwritten by the C program. Successful output is flushed/synced.

The shell wrapper independently checks actual device model/firmware, canonical source type/size/SHA, and the result size/SHA. It prepares a temporary file in a private subdirectory under an exclusive preparation lock, syncs and renames on the same filesystem. It never opens the system destination for writing. A damaged existing cache is refused, not replaced beneath a potentially running process.

## System integration and rollback

The system backend remains the previous guarded ext2 link-replacement transaction. It copies the already checked result into a root-owned runtime on p9, creates the early runonce job, verifies runtime manifest and backup, and only at boot before Explorer replaces the ext2 link with a verified root-owned file. SquashFS remains untouched. It restores the original mount options and checks `ro`.

On uninstall it atomically restores `../cramfs/lib/libopds_app_lib.so` with recorded link ownership. An interrupted `writing` phase restores the separately SHA-verified SquashFS original instead of guessing whether the write succeeded. Rooted preserves helper/attributes; Non-rooted removes the supported helper after completion, with explicit consent for existing root. Failures may retain recovery access. These checks do not guarantee power-loss/filesystem safety on real hardware.

## По-русски

Патчер получает все исходные таблицы и данные из оригинала самого пользователя. В распространяемом коде находятся алгоритм, собственные ARM-инструкции, контрольные суммы и минимальные проверки шести изменяемых участков — не полная библиотека и не её хвост.

Новый RX-сегмент, перенос таблиц ELF/EHABI и две ветви в коде воспроизводят прежний проверенный результат **побайтно**. Вторая строка показывает переданный OPDS `content type="text"`; её содержимое не ограничено авторами. Исходная классификация записей и навигация сохраняются.

Проприетарный оригинал внутри SquashFS не изменяется. В пользовательском кэше готовится отдельный файл; только проверенный результат передаётся прежнему защищённому системному установщику. При прерывании подготовки финального файла ещё нет; повторный запуск создаёт новую временную копию. При прерывании системной записи ранний обработчик восстанавливает оригинальную ссылку. Проверки компьютера не заменяют испытания питания, файловой системы и загрузки на ридере.

No automatic legal conclusion follows from using an algorithm/minimal patch rather than redistributing the library. See [third-party notices](../../THIRD_PARTY_NOTICES.md).
