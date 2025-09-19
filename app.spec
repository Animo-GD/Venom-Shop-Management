# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all necessary files for the nicegui library
datas = collect_data_files('nicegui')
# Add the icon file to datas
datas += [('icon.png', '.')]

# Collect all submodules from the 'src' directory
hiddenimports = collect_submodules('src')

a = Analysis(
	['app.py'],
	pathex=[],
	binaries=[],
	datas=datas,
	hiddenimports=hiddenimports,
	hookspath=[],
	hooksconfig={},
	runtime_hooks=[],
	excludes=[],
	noarchive=False,
	optimize=0,
	win_no_prefer_redirects=False,
	win_private_assemblies=False
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
	pyz,
	a.scripts,
	[],
	exclude_binaries=True,
	name='app',
	debug=False,
	bootloader_ignore_signals=False,
	strip=False,
	upx=True,
	runtime_tmpdir=None,
	console=False,  # This is correct for a GUI app (no black cmd window)
	disable_windowed_traceback=False,
	argv_emulation=False,
	target_arch=None,
	codesign_identity=None,
	entitlements_file=None,
	icon='icon.png'  # Make sure 'icon.png' is in the root directory
)
coll = COLLECT(
	exe,
	a.binaries,
	a.zipfiles,
	a.datas,
	strip=False,
	upx=True,
	upx_exclude=[],
	name='app'
)