# MSIX Packaging Guide

This project includes a dedicated MSIX helper script,
[`build_msix.py`](./build_msix.py), for preparing a Microsoft Store style
package from the current PyInstaller output.

## What Changed

The packaging flow is no longer tied to a single hard-coded executable path.

The current script supports:

- onefile outputs such as `dist/sanguosha.exe`
- onedir outputs such as `dist/sanguosha/sanguosha.exe`
- named builds from `python build.py --name <value>`
- explicit executable selection through `--exe-path`
- manifest executable renaming through `--package-executable`

## Prerequisites

You need the following on Windows:

1. Python and project dependencies
2. PyInstaller
3. Windows SDK tooling with `makeappx.exe`
4. `signtool.exe` if you plan to sign the package
5. Real MSIX artwork in the `Assets/` directory for a release-quality package

Official Microsoft references:

- [Create an app package with the MakeAppx tool](https://learn.microsoft.com/en-us/windows/msix/package/create-app-package-with-makeappx-tool)
- [SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool)

## Required Artwork

Provide these files in [`Assets/`](./Assets):

- `StoreLogo.png`
- `Square44x44Logo.png`
- `Square150x150Logo.png`
- `Wide310x150Logo.png`
- `SplashScreen.png`

`build_msix.py` can generate or reuse placeholder assets only when you
explicitly pass `--allow-placeholder-assets`. That path is meant for local
validation, not for a real Store submission.

## Step 1: Build the Desktop App

### Default onefile build

```powershell
python build.py
```

### Named onefile build

```powershell
python build.py --name sanguosha-store
```

### Named onedir build

```powershell
python build.py --onedir --name sanguosha-store
```

## Step 2: Package the Selected Build as MSIX

### Package by build name

Use this when the executable was created by `build.py --name ...`.

```powershell
python build_msix.py --exe-name sanguosha-store
```

### Package an explicit executable path

Use this when you want to point directly at a specific `.exe`.

```powershell
python build_msix.py --exe-path dist\sanguosha-store.exe
```

### Rename the executable inside the package manifest

This changes the filename referenced by the MSIX manifest, not the source build
name on disk.

```powershell
python build_msix.py --exe-name sanguosha-store --package-executable sanguosha.exe
```

### Local validation with placeholder artwork

```powershell
python build_msix.py --exe-name sanguosha-store --allow-placeholder-assets
```

## Signing

Signing is optional for local staging and required for a proper signed package
distribution workflow.

Recommended pattern:

```powershell
$env:SANGUOSHA_MSIX_CERT_PASSWORD = "your-password"
python build_msix.py `
  --exe-name sanguosha-store `
  --sign `
  --cert .\certificate.pfx `
  --password-env SANGUOSHA_MSIX_CERT_PASSWORD
Remove-Item Env:SANGUOSHA_MSIX_CERT_PASSWORD
```

You can also pass `--password`, but `--password-env` is safer for routine use.

## Output Behavior

### When `makeappx.exe` is available

The script produces:

- `sanguosha.msix`
- `msix_output/` staging directory

### When `makeappx.exe` is not available

The script still prepares `msix_output/` and exits after warning that the final
`.msix` package could not be produced.

This is useful when validating staging contents on a machine that does not yet
have the Windows SDK installed.

## Troubleshooting

### "built executable not found"

Run a matching build first, for example:

```powershell
python build.py --name sanguosha-store
python build_msix.py --exe-name sanguosha-store
```

Or point directly at the file with `--exe-path`.

### "missing required MSIX asset files"

Add the required files to `Assets/`, or use `--allow-placeholder-assets` for
local validation only.

### Wrong executable is packaged

Use one of these:

- `--exe-name` when packaging a named `build.py` output
- `--exe-path` when you want an explicit file
- `--package-executable` when you only need to rename the executable inside the
  package

## Suggested Release Flow

```powershell
python -m pip install ".[build]"
python build.py --name sanguosha-store
python build_msix.py --exe-name sanguosha-store --sign --cert .\certificate.pfx --password-env SANGUOSHA_MSIX_CERT_PASSWORD
```

Then validate the produced package before any Store submission.
