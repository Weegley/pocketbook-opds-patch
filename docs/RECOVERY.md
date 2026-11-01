# Recovery / Восстановление

## English

Only PB632 U632.6.11.2001 is supported. Keep a backup of personal files and know the reader's official firmware-recovery procedure before system installation. The owner reports all three v9 apps working; detailed failure/recovery tests were not provided. No recovery guarantee is made for flash damage, filesystem corruption or an unbootable interface.

### Normal removal

- System fix: run the same manager/version, choose Uninstall, allow its one reboot. This restores the original link and read-only mount flags. Deleting a manager app does not uninstall the fix.
- Online libraries: close the OPDS process (or reboot normally), remove the app and optionally `system/.opds-authors-611-open/standalone-open-v9/`. Never delete a mapped library/cache while the client is running. It needs no root and makes no system installation.

### Preparation failure

Read `OPDS_prepare_611.log`. A source version/size/hash mismatch is a refusal, not a request to bypass guards. Temporary files under a private `.patch.*` directory are never the installed system target. After closing OPDS, an interrupted/unusable **user cache** may be removed; it will be recreated. Keep the canonical SquashFS library untouched. Do not delete `.opds-authors-611-open` or its rooted counterpart while a manager operation is unfinished: the pending intent is stored there.

### Interrupted system operation

Keep `OPDS_*_611_install.log`, `OPDS_*_611_uninstall.log` and, when accessible with supported root, the private boot logs under `/mnt/secure/opds-authors-6.11/oneapp-*-boot.log.*`.

The protected job has queued/writing/cleanup-pending/complete phases. A boot interrupted during writing restores the canonical SHA-verified original link at the next eligible early boot. Runtime hash damage or a late hook refuses writes. Failure to restore `ro` or remove root does not report successful completion; root can remain for recovery.

Resume with the **same app version and root policy**, after saving logs and understanding the reported failure. Do not switch to an old Install/Keep/Restore app, force an unknown library, clear locks blindly or delete protected p9 state. The stock backup lives at `/mnt/secure/opds-authors-6.11/original.so`; the original remains in SquashFS. Existing `/mnt/secure/su` must match the supported pbjb hash/metadata.

Do not run low-level physical recovery against a live Explorer: its mapped inode can prevent a read-only remount. The guarded automatic recovery is designed to run before Explorer. If the normal GUI cannot start, using the `.app` may be impossible; recovery may require an independently available supported root method or the device's official firmware recovery. This project does not connect to your reader, flash firmware or supply a modified firmware image.

## Русский

Поддерживается только PB632 U632.6.11.2001. Перед системной установкой сохраните личные файлы и ознакомьтесь со штатной процедурой восстановления официальной прошивки для своего устройства. Владелец сообщил о работе всех трёх приложений v9; подробные испытания сбоев/восстановления не предоставлялись. Восстановление после повреждения памяти, файловой системы или отказа интерфейса не гарантируется.

### Обычное удаление

- Системный патч: тот же установщик/версия → «Удалить» → одна перезагрузка. Восстанавливаются исходная ссылка и read-only. Удаление установщика `.app` патч не удаляет.
- Online libraries: закройте OPDS либо штатно перезагрузитесь, удалите приложение и при желании `system/.opds-authors-611-open/standalone-open-v9/`. Кэш работающего клиента не удаляйте. Root и системная установка этому приложению не нужны.

### Ошибка подготовки

Сохраните `OPDS_prepare_611.log`. Несовпадение версии/размера/SHA — причина отказа; обходить защиту нельзя. Временный файл в `.patch.*` не является установленной системной библиотекой. После закрытия OPDS прерванный или повреждённый **пользовательский кэш** можно удалить, чтобы создать заново. Оригинал SquashFS не трогайте. Не удаляйте `.opds-authors-611-open`/вариант rooted во время незавершённой операции установщика: там хранится её намерение.

### Прерванная системная операция

Сохраните журналы `OPDS_*_611_install.log`, `OPDS_*_611_uninstall.log`; при доступном поддерживаемом root также сохраните `/mnt/secure/opds-authors-6.11/oneapp-*-boot.log.*`.

Защищённое задание проходит queued/writing/cleanup-pending/complete. Прерванная фаза writing при следующей подходящей ранней загрузке восстанавливает ссылку на проверенный оригинал. При повреждённом runtime или позднем hook запись запрещается. Невозможность вернуть `ro` или удалить root не объявляется успехом; root может остаться для восстановления.

Продолжайте **той же версией и с той же политикой root**, сохранив логи и разобрав ошибку. Не используйте старые Install/Keep/Restore, не применяйте патч к неизвестному файлу, не сбрасывайте вслепую блокировки и не удаляйте защищённое состояние p9. Копия оригинала хранится в `/mnt/secure/opds-authors-6.11/original.so`; исходник остаётся в SquashFS. `/mnt/secure/su` должен соответствовать поддерживаемому pbjb по SHA/метаданным.

Не запускайте низкоуровневое физическое восстановление при работающем Explorer: отображённый inode может мешать возврату read-only. Автоматическое восстановление рассчитано на раннюю загрузку до Explorer. Если GUI не запускается, `.app` может быть недоступен; потребуется независимо доступный поддерживаемый root либо штатное восстановление официальной прошивки. Проект сам не подключается к устройству, не прошивает его и не создаёт модифицированную прошивку.
