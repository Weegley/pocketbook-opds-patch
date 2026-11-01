# Firmware evidence: currentLang reads global.cfg / language, default en.
# iv2sh ReadConfig prints the value on stdout and closes without saving.
opds_select_language() {
    opds_locale=
    # This stock command may return 1 even when the read succeeds.
    opds_locale=$(iv2sh ReadConfig /mnt/ext1/system/config/global.cfg language en 2>/dev/null) || :
    opds_locale=$(printf '%s\n' "$opds_locale" | tr -d '\r' | awk 'NF {last=$0} END {gsub(/^[ \t]+|[ \t]+$/, "", last); print tolower(last)}')
    case "$opds_locale" in
        ru|ru_*|ru-*|ru.*) OPDS_UI_LANGUAGE=ru;;
        *) OPDS_UI_LANGUAGE=en;;
    esac
    export OPDS_UI_LANGUAGE
}

opds_text() {
    case "${OPDS_UI_LANGUAGE:-en}/$1" in
        ru/cancel) printf '%s\n' 'Отмена';;
        */cancel) printf '%s\n' 'Cancel';;
        ru/install) printf '%s\n' 'Установить';;
        */install) printf '%s\n' 'Install';;
        ru/uninstall) printf '%s\n' 'Удалить';;
        */uninstall) printf '%s\n' 'Uninstall';;
        ru/busy) printf '%s\n' 'Установщик уже запущен.';;
        */busy) printf '%s\n' 'The installer is already running.';;
        ru/wrong_firmware) printf '%s\n' 'Неподходящая прошивка.';;
        */wrong_firmware) printf '%s\n' 'Unsupported firmware.';;
        ru/original_mismatch) printf '%s\n' 'Оригинальная библиотека не совпадает.';;
        */original_mismatch) printf '%s\n' 'The original library checksum does not match.';;
        ru/unknown_library) printf '%s\n' 'Системная библиотека неизвестна. Изменения запрещены.';;
        */unknown_library) printf '%s\n' 'Unknown system library. No changes are allowed.';;
        ru/bad_state) printf '%s\n' 'Повреждено состояние установщика.';;
        */bad_state) printf '%s\n' 'The installer state is damaged.';;
        ru/rolled_back) printf '%s\n' 'Операция не завершилась: автоматически восстановлена исходная библиотека, root удалён. Сохраните журнал операции.';;
        */rolled_back) printf '%s\n' 'The operation did not complete. The original library was restored automatically and root was removed. Save the operation log.';;
        ru/completed) printf '%s\n' 'Операция завершена: библиотека проверена, системный раздел только для чтения, root удалён. Проверьте штатный OPDS.';;
        */completed) printf '%s\n' 'Operation complete: the library is verified, the system partition is read-only, and root is removed. Check the built-in OPDS client.';;
        ru/install_remove_root) printf '%s\n' 'Включить вторую строку с текстом каталога в штатном OPDS? Временный root будет удалён после операции.';;
        */install_remove_root) printf '%s\n' 'Enable the second line of catalog text in native OPDS? Temporary root will be removed after the operation.';;
        ru/uninstall_remove_root) printf '%s\n' 'Удалить патч второй строки OPDS и вернуть штатную библиотеку? Временный root будет удалён после операции.';;
        */uninstall_remove_root) printf '%s\n' 'Remove the OPDS second-line patch and restore the original library? Temporary root will be removed after the operation.';;
        ru/install_keep_root) printf '%s\n' 'Включить вторую строку с текстом каталога в штатном OPDS? Существующий root будет сохранён.';;
        */install_keep_root) printf '%s\n' 'Enable the second line of catalog text in native OPDS? Existing root access will be kept.';;
        ru/uninstall_keep_root) printf '%s\n' 'Удалить патч второй строки OPDS и вернуть штатную библиотеку? Существующий root будет сохранён.';;
        */uninstall_keep_root) printf '%s\n' 'Remove the OPDS second-line patch and restore the original library? Existing root access will be kept.';;
        ru/log_symlink) printf '%s\n' 'Неожиданная ссылка вместо журнала.';;
        */log_symlink) printf '%s\n' 'Unexpected symbolic link at the log path.';;
        ru/helper_symlink) printf '%s\n' 'Неожиданная ссылка root-helper.';;
        */helper_symlink) printf '%s\n' 'Unexpected root-helper symbolic link.';;
        ru/bootstrap) printf '%s\n' 'Сейчас будет получен временный root и подготовлена перезагрузка. После загрузки операция завершится автоматически; root будет удалён. Не выключайте питание.';;
        */bootstrap) printf '%s\n' 'Temporary root will now be obtained and a reboot prepared. The operation will complete automatically during startup, then root will be removed. Do not turn off the power.';;
        ru/bootstrap_returned) printf '%s\n' 'Запрос root/перезагрузки вернулся. Если ридер не перезагрузился, сохраните журнал. При подготовленном задании можно перезагрузить вручную; повторный запуск использует то же задание.';;
        */bootstrap_returned) printf '%s\n' 'The root or reboot request returned. If the reader did not restart, save the log. If a job was prepared, you can reboot manually; running the app again reuses that job.';;
        ru/foreign_helper_remove) printf '%s\n' 'Обнаружен другой root-helper. Для безопасности он не будет использован или удалён. Смотрите журнал.';;
        */foreign_helper_remove) printf '%s\n' 'A different root helper was found. It will not be used or removed. See the log.';;
        ru/foreign_helper_keep) printf '%s\n' 'Обнаружен другой root-helper. Для безопасности он не будет использован или изменён. Смотрите журнал.';;
        */foreign_helper_keep) printf '%s\n' 'A different root helper was found. It will not be used or changed. See the log.';;
        ru/stage_failed) printf '%s\n' 'Подготовка не завершена. Root пока сохранён для восстановления. Смотрите журнал операции.';;
        */stage_failed) printf '%s\n' 'Preparation did not complete. Root has been kept for recovery. See the operation log.';;
        ru/queued_remove) printf '%s\n' 'Операция подготовлена. Сейчас ридер перезагрузится: библиотека будет заменена до запуска оболочки, затем root будет удалён. Не выключайте питание во время загрузки.';;
        */queued_remove) printf '%s\n' 'The operation is ready. The reader will now reboot. The library will be replaced before the interface starts, then root will be removed. Do not turn off the power during startup.';;
        ru/queued_keep) printf '%s\n' 'Операция подготовлена. Сейчас ридер перезагрузится: библиотека будет заменена до запуска оболочки, существующий root будет сохранён. Не выключайте питание во время загрузки.';;
        */queued_keep) printf '%s\n' 'The operation is ready. The reader will now reboot. The library will be replaced before the interface starts, and existing root access will be kept. Do not turn off the power during startup.';;
        ru/root_required) printf '%s\n' 'Нужен уже установленный root-helper /mnt/secure/su. Эта версия root не получает. Используйте Non-rooted patch.';;
        */root_required) printf '%s\n' 'An existing root helper at /mnt/secure/su is required. This version does not obtain root. Use Non-rooted patch instead.';;
        ru/firmware_required) printf '%s\n' 'Нужна прошивка U632.6.11.2001.';;
        */firmware_required) printf '%s\n' 'Firmware U632.6.11.2001 is required.';;
        ru/model_required) printf '%s\n' 'Поддерживается только PocketBook 632.';;
        */model_required) printf '%s\n' 'Only PocketBook 632 is supported.';;
        ru/cache_symlink) printf '%s\n' 'Неожиданная ссылка вместо рабочего каталога.';;
        */cache_symlink) printf '%s\n' 'Unexpected symbolic link at the working directory path.';;
        ru/storage_unavailable) printf '%s\n' 'Нет доступа к внутренней памяти.';;
        */storage_unavailable) printf '%s\n' 'Internal storage is not accessible.';;
        ru/extraction_busy) printf '%s\n' 'Другое приложение OPDS ещё распаковывается.';;
        */extraction_busy) printf '%s\n' 'Another OPDS app is still extracting its files.';;
        ru/cache_damaged) printf '%s\n' 'Повреждён кэш OPDS: удалите system/.opds-authors-611-open/standalone-open-v9 и повторите запуск.';;
        */cache_damaged) printf '%s\n' 'The OPDS cache is damaged. Delete system/.opds-authors-611-open/standalone-open-v9 and try again.';;
        ru/extract_create_failed) printf '%s\n' 'Не удалось распаковать приложение.';;
        */extract_create_failed) printf '%s\n' 'Could not create the application extraction directory.';;
        ru/app_damaged) printf '%s\n' 'Повреждён файл приложения.';;
        */app_damaged) printf '%s\n' 'The application file is damaged.';;
        ru/app_read_failed) printf '%s\n' 'Ошибка чтения приложения.';;
        */app_read_failed) printf '%s\n' 'Could not read the application file.';;
        ru/app_checksum_failed) printf '%s\n' 'Неверная контрольная сумма приложения.';;
        */app_checksum_failed) printf '%s\n' 'The application checksum does not match.';;
        ru/extract_failed) printf '%s\n' 'Ошибка распаковки.';;
        */extract_failed) printf '%s\n' 'Extraction failed.';;
        ru/component_damaged) printf '%s\n' 'Повреждён компонент приложения.';;
        */component_damaged) printf '%s\n' 'An application component is damaged.';;
        ru/standalone_busy) printf '%s\n' 'OPDS уже распаковывается другим запуском.';;
        */standalone_busy) printf '%s\n' 'Another OPDS launch is already creating the cache.';;
        ru/cache_save_failed) printf '%s\n' 'Ошибка сохранения кэша OPDS.';;
        */cache_save_failed) printf '%s\n' 'Could not save the OPDS cache.';;
        ru/standalone_unsupported) printf '%s\n' 'Повреждён пакет или не поддерживается прошивка.';;
        */standalone_unsupported) printf '%s\n' 'The package is damaged or the firmware is unsupported.';;
        ru/prepare_failed) printf '%s\n' 'Не удалось подготовить библиотеку OPDS. Исходная библиотека и системная ссылка не изменены.';;
        */prepare_failed) printf '%s\n' 'Could not prepare the OPDS library. The original library and system link were not changed.';;
        ru/existing_root_warning) printf '%s\n' 'На устройстве уже установлен root. Non-rooted удалит его после успешной операции, даже если вы установили его ранее. Для сохранения root нажмите Отмена и используйте Rooted patch. Подтверждаете удаление root?';;
        */existing_root_warning) printf '%s\n' 'Root is already installed. Non-rooted will remove it after success, even if you installed it earlier. To keep root, cancel and use Rooted patch. Confirm removal of existing root?';;
        ru/confirm_remove_root) printf '%s\n' 'Подтверждаю удаление root';;
        */confirm_remove_root) printf '%s\n' 'Confirm root removal';;
        ru/pbjb_missing) printf '%s\n' 'Нужны оригинальные jailbreak и su от pbjb. Поместите проверенные файлы в system/opds-pbjb/8f1fb889d575237f2b292e88df6aabf552142d87/ или используйте локальную сборку. Смотрите инструкцию PBJB.';;
        */pbjb_missing) printf '%s\n' 'Original pbjb jailbreak and su are required. Put verified files in system/opds-pbjb/8f1fb889d575237f2b292e88df6aabf552142d87/ or use a local build. See the PBJB instructions.';;
        *) printf '%s\n' "[$1]";;
    esac
}
