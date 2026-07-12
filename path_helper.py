import os
import sys


def resource_path(relative_path: str) -> str:
    """获取打包后资源的绝对路径。

    PyInstaller --onefile 模式下，资源被解压到 sys._MEIPASS 临时目录。
    开发模式下，资源在脚本所在目录。
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def get_app_data_dir() -> str:
    """获取用户数据目录（用于存储 config.json 等可写文件）。

    Windows: %APPDATA%/GitNoteEditor
    Linux/Mac: ~/.gitnoteeditor
    开发模式: 脚本所在目录
    """
    if getattr(sys, 'frozen', False):
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                data_dir = os.path.join(appdata, 'GitNoteEditor')
            else:
                data_dir = os.path.join(os.path.expanduser('~'), '.gitnoteeditor')
        else:
            data_dir = os.path.join(os.path.expanduser('~'), '.gitnoteeditor')
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return os.path.dirname(os.path.abspath(__file__))


def get_data_file_path(filename: str) -> str:
    """获取用户数据文件的完整路径。"""
    return os.path.join(get_app_data_dir(), filename)
