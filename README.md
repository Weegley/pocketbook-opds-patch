# PocketBook OPDS Patch

**English** | [Русский](README.ru.md)

**PocketBook 632 (Touch HD 3), firmware U632.6.11.2001 only.**

Enables a second line below navigation entry titles in the native OPDS client, showing the catalog's `content type="text"`. In [inpx-web](https://github.com/bookpauk/inpx-web), a book's folder supplies its author(s); other folders may supply text such as book counts. The original **book folder → “Book” feed → details/download** navigation is preserved. No server changes are needed.

## Download and use

Get the apps from the [latest release](https://github.com/Weegley/pocketbook-opds-patch/releases/latest).

| App | Choose it when… |
| --- | --- |
| **Online libraries.app** | You want a shortcut that opens the native OPDS interface directly. No root, system installation or reboot. |
| **Non-rooted patch.app** | You want to install/remove the fix in the system OPDS client. Obtains root if needed and removes it after success. |
| **Rooted patch.app** | You already have the supported pbjb root and want to keep it. Installs/removes the system fix without changing root. |

1. Copy the chosen `.app` to `applications/` in reader internal storage. No extra folders are needed.
2. Safely disconnect USB and launch it from Applications.
3. Online libraries opens OPDS. A patch manager offers **Install** or **Uninstall** based on the current library; confirm and allow **one reboot**.

**Non-rooted also removes previously installed root after explicit confirmation. To keep root, use Rooted.** Rooted requires the compatible pbjb `/mnt/secure/su`; arbitrary root helpers are not supported.

Dialogs are Russian when the reader interface is Russian, English otherwise. The proprietary OPDS library is **not bundled**: each app prepares a checked copy from the reader's original. Back up your data, keep the battery charged and do not interrupt system installation.

## Remove

- **System fix:** run the same manager, select **Uninstall** and allow its reboot. Deleting the `.app` alone does not remove the patch.
- **Online libraries:** close OPDS, then delete the `.app`. Optionally remove its cache: `system/.opds-authors-611-open/standalone-open-v9/`.

For failures, keep the `OPDS_*.log` files in internal storage and follow [recovery instructions](docs/RECOVERY.md). Resume an interrupted operation with the same manager/version.

## Build yourself

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

Debian/Ubuntu x86-64:

```sh
sh build.sh
```

Python, Zig and pbjb are downloaded automatically with pinned SHA-256 checks, inside the project only. No global installs. Apps and checksums appear in `dist/`. The owner confirmed automatic Windows/Linux builds and all three apps working on the reader.

[Build details](docs/BUILD.md) · [Русская инструкция](docs/BUILD.ru.md) · [Checksums](SHA256SUMS.txt)

## Credits and license

Root acquisition uses unchanged components from **[ezdiy/pbjb](https://github.com/ezdiy/pbjb)**; see [pinned revision and hashes](docs/PBJB.md). Original project code is [MIT](LICENSE). Third-party components retain their own rights; see [notices](THIRD_PARTY_NOTICES.md). Unofficial project, not affiliated with PocketBook.
