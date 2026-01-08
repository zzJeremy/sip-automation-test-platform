# main.py
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from db.database import Database
from core.test_framework import TestFramework
from config import Config

def main():
    # Initialize configuration
    config = Config()
    
    # Initialize database
    db = Database(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    
    # Initialize test framework
    test_framework = TestFramework(db)
    
    # Initialize GUI
    app = QApplication(sys.argv)
    window = MainWindow(test_framework)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()