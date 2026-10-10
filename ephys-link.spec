"""PyInstaller spec file for ephys-link."""

import importlib.util
import os
import sys
import tomllib

# --- Version from pyproject.toml ---
with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)
version = pyproject["project"]["version"]

app_name = f"ephys-link-v{version}"

# --- Locate sensapex compiled binary ---
sensapex_spec = importlib.util.find_spec("sensapex")
if sensapex_spec is None or sensapex_spec.origin is None:
    raise RuntimeError("sensapex module not found in build environment")
sensapex_dir = os.path.dirname(sensapex_spec.origin)

if sys.platform == "darwin":
    raise RuntimeError("macOS builds are not supported: sensapex does not ship a macOS binary")
if sys.platform == "win32":
    lib_name = "um.dll"
else:
    lib_name = "libum.so"
lib_path = os.path.join(sensapex_dir, lib_name)

if not os.path.exists(lib_path):
    raise RuntimeError(f"Sensapex binary not found: {lib_path}")

# --- PyInstaller build ---
a = Analysis(
    ["src/ephys_link/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[(lib_path, "sensapex")],
    hiddenimports=["sensapex"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[lib_name],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[lib_name],
    name=app_name,
)
