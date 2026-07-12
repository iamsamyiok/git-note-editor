from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('pynput')
hiddenimports += ['pynput.keyboard', 'pynput.mouse']