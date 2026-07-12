import os
import sys
import subprocess
import urllib.request
import tempfile

GIT_DOWNLOAD_URL_TEMPLATE = (
    "https://mirrors.tuna.tsinghua.edu.cn/github-release/git-for-windows/git/"
    "LatestRelease/Git-{version}-{arch}-bit.exe"
)

_creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _find_git() -> str:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        exe = os.path.join(path, "git.exe" if sys.platform == "win32" else "git")
        if os.path.isfile(exe):
            return exe
    for candidate in [
        "C:\\Program Files\\Git\\cmd\\git.exe",
        "C:\\Program Files (x86)\\Git\\cmd\\git.exe",
    ]:
        if os.path.isfile(candidate):
            return candidate
    return ""


def check_git() -> tuple:
    exe = _find_git()
    if not exe:
        return False, "", "PATH 中未找到 git，请安装 Git for Windows。"
    try:
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_creationflags,
        )
        return True, exe, result.stdout.strip()
    except Exception as e:
        return False, "", f"git 环境异常：{e}"


def _is_64bit_windows() -> bool:
    return sys.maxsize > 2**32


def install_git(parent=None) -> bool:
    try:
        arch = "64" if _is_64bit_windows() else "32"
        url = GIT_DOWNLOAD_URL_TEMPLATE.format(version="2.47.1", arch=arch)

        tmp_dir = tempfile.gettempdir()
        installer_path = os.path.join(tmp_dir, "Git-Installer.exe")
        urllib.request.urlretrieve(url, installer_path)

        subprocess.run(
            [
                installer_path,
                "/VERYSILENT",
                "/NORESTART",
                "/NOCANCEL",
                "/SP-",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
                '/COMPONENTS="icons,ext\\shellhere,assoc,assoc_sh"',
                '/DIR="C:\\Program Files\\Git"',
            ],
            check=True,
            timeout=300,
            creationflags=_creationflags,
        )

        os.remove(installer_path)

        os.environ["PATH"] = (
            "C:\\Program Files\\Git\\cmd;" + os.environ.get("PATH", "")
        )

        return True
    except Exception:
        return False
