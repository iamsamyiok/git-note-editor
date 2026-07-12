# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hiddenimports = []

# PyQt5 全部子模块
hiddenimports += collect_submodules('PyQt5')
hiddenimports += [
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtPrintSupport',
    'PyQt5.QtSvg',
]

# requests 及其依赖
hiddenimports += collect_submodules('requests')
hiddenimports += collect_submodules('urllib3')
hiddenimports += collect_submodules('charset_normalizer')
hiddenimports += [
    'certifi',
    'idna',
]

# pynput 及其平台后端
hiddenimports += collect_submodules('pynput')
hiddenimports += [
    'pynput.keyboard',
    'pynput.mouse',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'pynput.keyboard._darwin',
    'pynput.mouse._darwin',
    'pynput.keyboard._xorg',
    'pynput.mouse._xorg',
]

# beautifulsoup4
hiddenimports += collect_submodules('bs4')
hiddenimports += ['bs4', 'lxml']

# PIL
hiddenimports += collect_submodules('PIL')
hiddenimports += ['PIL.Image', 'PIL.ImageQt']

# 项目自身模块（确保全部被打包）
hiddenimports += [
    'app',
    'models',
    'version_manager',
    'git_manager',
    'graph_widget',
    'editor_widget',
    'dialogs',
    'screenshot_widget',
    'settings_dialog',
    'bookmark_widget',
    'bookmark_manager',
    'bookmark_model',
    'bookmark_dialog',
    'chat_widget',
    'chat_manager',
    'chat_model',
    'chat_message_widget',
    'ai_service',
    'ocr_manager',
    'cloudcode_executor',
    'cloudcode_dialog',
    'cloudcode_result',
    'reminder_widget',
    'reminder_model',
    'reminder_scheduler',
    'reminder_dialog',
    'task_manager',
    'task_dialog',
    'git_installer',
    'path_helper',
]

datas = [
    ('icon.png', '.'),
]

# 收集 PyQt5 数据文件（插件、翻译等）
datas += collect_data_files('PyQt5')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GitNoteEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
