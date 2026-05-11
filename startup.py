import sys
import os
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtGui import QIcon, QPixmap

def _load_env_file(path: str):
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))
    except Exception:
        pass


# Load env from project root first, then user profile override.
project_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
user_env_path = os.path.expanduser('~/.autoptz/.env')
_load_env_file(project_env_path)
_load_env_file(user_env_path)

from views.homepage.main_window import AutoPTZ_MainWindow
import shared.constants as constants


def main():
    """
    Starts the AutoPTZ Application
    """
    app = QApplication(sys.argv)
    window = AutoPTZ_MainWindow()
    window.setWindowIcon(QIcon(constants.ICON_PNG))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
