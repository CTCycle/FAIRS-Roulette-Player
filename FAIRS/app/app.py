import sys
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from FAIRS.app.client.window import MainWindow
from FAIRS.app.constants import UI_PATH
from FAIRS.app.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == "__main__":  
    app = QApplication(sys.argv) 

    # setup stylesheet
    extra = {'density_scale': '-1'}
    apply_stylesheet(app, theme='dark_yellow.xml', extra=extra)

    main_window = MainWindow(UI_PATH)   
    main_window.show()
    sys.exit(app.exec())

   
