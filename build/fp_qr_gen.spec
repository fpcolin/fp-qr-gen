# PyInstaller spec. Build from the repo root with:
#     pyinstaller build\fp_qr_gen.spec --noconfirm --clean

block_cipher = None

a = Analysis(
    # .pyw suppresses the console when double-clicking the source on Windows.
    # It has no bearing on the built exe - console=False below does that job.
    # Note updater.py must keep its .py extension: Python's import system only
    # recognises .py as a source suffix, so a .pyw module is not importable.
    ['..\\src\\fp_qr_gen.pyw'],
    pathex=['..\\src'],
    binaries=[],
    # ('source', 'destination in bundle'). '.' puts them beside the exe, which
    # is exactly where resource_path() looks via sys._MEIPASS.
    datas=[
        ('..\\src\\fp.ico', '.'),
        ('..\\src\\fp_logo.png', '.'),
    ],
    hiddenimports=['updater'],
    hookspath=[],
    runtime_hooks=[],
    # Trimming these keeps the bundle small. Do NOT add http, email, ssl,
    # urllib or encodings here - the updater needs all of them.
    excludes=[
        'numpy', 'scipy', 'pandas', 'matplotlib',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'sphinx', 'setuptools', 'pip',
        'tkinter.test', 'test', 'lib2to3', 'pydoc_data',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # onedir: keeps startup fast, AV happier
    name='FPQRGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # UPX packing is a major AV false-positive trigger
    console=False,                  # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='..\\src\\fp.ico',
    version='version_info.txt',     # populates the Details tab in file properties
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FPQRGenerator',
)
