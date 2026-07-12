from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('beautifulsoup4')
hiddenimports += ['bs4', 'lxml']