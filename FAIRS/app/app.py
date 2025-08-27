import sys
from PySide6.QtWidgets import QApplication

# [SETTING WARNINGS]
import warnings

warnings.simplefilter(action="ignore", category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.app.client.window import apply_style, MainWindow
from FAIRS.app.constants import UI_PATH


# [RUN MAIN]
###############################################################################
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app = apply_style(app)
    main_window = MainWindow(UI_PATH)
    main_window.show()
    sys.exit(app.exec())
