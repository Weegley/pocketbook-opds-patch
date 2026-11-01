# Validation record / Проверки

This document describes offline checks performed on Windows and separately records owner reports. The agent did not connect to the reader or execute extracted ARM/pbjb files. The previously tested universal-v8 binaries were read as immutable references and not overwritten.

## Owner report: 1 November 2026

The owner [reported Standalone/Online libraries and both Non-rooted/Rooted variants working](device-user-report-20261101.json). No new device logs or per-operation recovery matrix accompanied that statement. Record this as confirmation of the reported application behavior, without inferring power-loss recovery or every install/uninstall branch was tested. Runtime app sources were not changed when fixing build-entrypoint diagnostics.

The owner subsequently confirmed that **automatic builds completed successfully on both Windows and Linux**. This supersedes the earlier pending end-to-end build status below. No Linux artifact hashes or full logs accompanied the brief report, so cross-OS byte equality is not inferred from it. Agent-run Windows checks and historical network limitations remain separate evidence.

## Exact reference identity

- Host-native build of the new C patcher consumed the private exact 598364-byte firmware original. Its 610748-byte result matched the universal-v8 patched library byte for byte, SHA-256 `c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5`.
- Subsequent private comparison is implemented entirely in memory (`--compare`); no proprietary binary is needed in the public repository, export or synthetic fixtures. The development-only transient output used for the first comparison was removed.
- The source-built ARM launcher matches the entire old launcher, SHA-256 `4e973c3616e728a4c7954b6a0e888bd64df55841485743adfb74d2eed8cfdc43`, size 4928. Its `.text`, dynamic dependencies and ABI-version references match as well. Firmware linking libraries were replaced by project-owned link-only declaration stubs, not distributed runtime stubs.
- The new patcher's 33 ARM instructions are assembled separately and compared against the words in the C source. No ARM execution is implied by this check.

## Offline suites

Final Windows run on 1 November 2026: **193 checks passed**, with **49 protected transaction invocations**, plus the compiled callback model. The run included private original/reference comparison. A separate checkout extracted from the source ZIP, with only declared tool/pbjb dependencies provisioned and no firmware/reference inputs, passed **189 checks and 49 transaction invocations**. The four-check difference is the explicitly skipped private-reference group, not a failure. All three apps from that separate source tree are byte-identical to the primary build.

The final machine-readable report is `build/test-receipt.json` (generated, ignored by Git). It records the check count, transaction invocations, source SHA-256 and whether private reference comparison was performed. `build/build-receipt.json` records Python/platform/compiler and public/private artifact hashes. Update this record if sources change.

Build-entrypoint follow-up: **17 isolated preflight/error tests passed**, including missing dependencies, wrong hashes/version, network failure, command failure, check-only behavior and preservation of existing apps. **Three real PowerShell invocations passed** their expected outcomes (missing Zig, missing Python, ready check). A normal native Windows build then completed successfully and reproduced all three recorded app hashes. These follow-up checks did not change runtime sources and do not imply a fresh run of the 193 installer/package checks. Full command/error output is appended to `build/build.log`; the PowerShell checks are recorded locally in `build/preflight-powershell-tests.json`.

Full-auto follow-up: missing inputs are now prepared by default, including a pinned project-local Python distribution before Python build code runs. Current fast suites passed **18 build/preflight tests** and **13 portable-Python bootstrap tests**. Bootstrap tests use synthetic archives and replacement network/interpreter boundaries, exercising PowerShell extraction/activation, cached reuse, SHA failures, traversal rejection, partial-install refusal and Linux shell control flow. **Four real PowerShell entrypoint cases** verified check/offline non-download behavior and explicit-interpreter overrides (`build/full-auto-entrypoint-tests.json`). A native Windows build using already available declared tools completed and reproduced the three app hashes. This does not claim that a real Linux Python executable was run on Windows.

Coverage includes:

- SHA self-test; wrong model/firmware/size/SHA and repeated-patch refusals; exclusive output creation;
- private original/reference comparison without writing firmware into the repository;
- public app archive safety, manifests, deterministic packaging, absence of the PocketBook library and exact upstream pbjb only in Non-rooted;
- original core installer roundtrip, backup, link restore, mount/device/namespace/hash/space guards and simulated write/remount failures;
- actual protected stage/boot/apply/recovery shell paths for both root policies, repeated stage, deferred uninstall, simulated torn write, late boot, damaged runtime and root-cleanup retry;
- Rooted preserving root without chattr, Non-rooted temporary bootstrap/removal, and refusal without explicit existing-root consent;
- root-free library preparation/cache reuse with a harmless replacement of the ARM executable boundary; interruption/wrong output/corrupt cache/original/version refusals;
- external pbjb missing/wrong/verified component paths using visibly synthetic, non-executable fixtures;
- RU/EN string pairs, Unicode, native config-read success with exit 1, localized install/uninstall dispatch and cancellation of existing-root removal;
- complete self-extracting package verification and language change with an existing cache using a harmless shell launch stub;
- source callback model: copy/destroy lifetime, RTTI, activation redraw, native book opening, passthrough and malformed-request refusal.

OS boundaries are models: Windows fixtures do not prove Linux VFS behavior, real uid/ownership, immutable flags, flock, mount operations, flash durability or actual reboot ordering. The synthetic installer fixtures deliberately replace firmware identities and byte contents; they do not validate the real library transform. That is covered separately by the private C comparison.

## Platform and download limits

Verified environment: native Windows PowerShell, CPython 3.14.2, Zig 0.13.0 and hash-pinned BusyBox-w64. Compiler caches and temporary files were confined to the project. Existing local compiler/upstream files were used; **fresh network tool/pbjb downloading was not executed successfully in this network-restricted environment**. Setup verifies pinned SHA and refuses a mutable upstream file that no longer matches.

Linux/WSL was not installed. Linux scripts/configuration are supplied, but a clean Linux build and cross-OS hash equality have not been executed. The separately documented portable embedded Python option was not executed either. These are explicit validation limits, not completed tests.

The owner subsequently reported the Windows build with `-Setup` successfully creating the apps. The new full-auto launcher was also used to attempt the pinned official Python download here, but this environment rejected the network/TLS connection; no runtime was activated. Real fresh Python-download/extraction on Windows and Linux still requires validation in an unrestricted network environment. The implemented Windows default uses the complete official portable ZIP, not the earlier manually documented embeddable option. Downloaded distributions remain ignored build inputs, absent from Git and exports.

The separate app build also succeeded in a checkout path containing spaces and produced identical apps. The inherited virtual mount text fixtures require a path without whitespace; the full separate suite was therefore run in a path without spaces, and this restriction is checked explicitly and documented in both build guides. This is a host test-model limitation, not a reader cache-path change.

## Further device checklist

The owner has reported all v9 apps working and previously confirmed RU/EN selection. The following checklist can be used for a more detailed log-backed matrix; individual checks below are not inferred from the brief report:

1. Online libraries: no root installed, first-launch preparation of the real library, successful OPDS start, cache reuse and RU↔EN switching.
2. Navigate in inpx-web: second line on the book folder, folder → “Книга” → details, download and open a book through the native reader callback.
3. Rooted: exact existing pbjb helper; one-reboot install/uninstall, correct original backup/link/owner and `ro`, root bytes/permissions/attributes unchanged.
4. Non-rooted default app: exact embedded pbjb, root bootstrap, one-reboot install/uninstall and root cleanup. Optional external mode: missing/wrong component refusal and separately supplied exact files.
5. Existing root: cancel the extra removal confirmation and verify root/system remain unchanged; then test explicit confirmation if deletion is intended.
6. Compare embedded and optional external-component variants on the reader, if the latter is used.
7. Review cumulative public/private logs and recovery behavior. Do not deliberately interrupt power on a production reader to imitate the offline crash model.

Offline checks alone do not establish hardware behavior or crash recovery.

## По-русски

Подтверждены побайтное совпадение результата патчера с universal-v8 и всего пересобранного загрузчика с прежним. Выполнены нативные Windows-проверки, без подключения к ридеру и без исполнения ARM/pbjb. Машинный отчёт содержит количество проверок и SHA исходников. Модели Linux проверяют ветвление настоящих shell-скриптов, но не реальную файловую систему, питание и загрузку устройства.

Итог: **193 проверки и 49 вызовов транзакции** в основном проекте; **189 проверок и 49 вызовов** из отдельной распакованной копии исходников без частных файлов прошивки. Разница — четыре явно пропущенные проверки частного эталона. Все три полученных приложения совпали побайтно. Полный набор shell-фикстур требует путь без пробелов; сама сборка приложений с пробелами в пути также прошла и дала те же байты.

Владелец сообщил о работе всех трёх приложений v9; сообщение сохранено отдельно. Подробные журналы и матрица восстановления не передавались, поэтому каждый пункт списка выше не объявляется испытанным автоматически. Linux и portable embedded Python отдельно не запускались; реальные загрузки инструментов/компонентов по сети в текущем окружении не подтверждены. Исправление предпроверки сборщика не меняет runtime приложений.
