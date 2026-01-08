# ui/main_window.py
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QTableWidget, QTableWidgetItem, QLabel,
                           QComboBox, QTextEdit, QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt
from core.test_framework import TestFramework
import json

class MainWindow(QMainWindow):
    def __init__(self, test_framework: TestFramework):
        super().__init__()
        self.test_framework = test_framework
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Softswitch System Automated Testing Platform')
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Test Case Management Tab
        test_case_tab = QWidget()
        test_case_layout = QVBoxLayout(test_case_tab)
        
        # Test case creation section
        create_group = QWidget()
        create_layout = QHBoxLayout(create_group)
        
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(['SIP', 'ISUP', 'ISDN'])
        create_layout.addWidget(QLabel('Protocol:'))
        create_layout.addWidget(self.protocol_combo)
        
        self.test_script_edit = QTextEdit()
        create_layout.addWidget(QLabel('Test Script:'))
        create_layout.addWidget(self.test_script_edit)
        
        create_btn = QPushButton('Create Test Case')
        create_btn.clicked.connect(self.create_test_case)
        create_layout.addWidget(create_btn)
        
        test_case_layout.addWidget(create_group)

        # Test case list
        self.test_case_table = QTableWidget()
        self.test_case_table.setColumnCount(4)
        self.test_case_table.setHorizontalHeaderLabels(['ID', 'Name', 'Protocol', 'Actions'])
        test_case_layout.addWidget(self.test_case_table)
        
        tab_widget.addTab(test_case_tab, "Test Case Management")

        # Test Execution Tab
        execution_tab = QWidget()
        execution_layout = QVBoxLayout(execution_tab)
        
        # Control buttons
        control_group = QWidget()
        control_layout = QHBoxLayout(control_group)
        
        run_btn = QPushButton('Run Selected Tests')
        run_btn.clicked.connect(self.run_selected_tests)
        control_layout.addWidget(run_btn)
        
        stop_btn = QPushButton('Stop Execution')
        stop_btn.clicked.connect(self.stop_execution)
        control_layout.addWidget(stop_btn)
        
        execution_layout.addWidget(control_group)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(['Test ID', 'Name', 'Status', 'Time', 'Error'])
        execution_layout.addWidget(self.results_table)
        
        tab_widget.addTab(execution_tab, "Test Execution")

        self.refresh_test_cases()

    def create_test_case(self):
        try:
            protocol = self.protocol_combo.currentText()
            script = self.test_script_edit.toPlainText()
            
            test_case_id = self.test_framework.create_test_case(
                name=f"Test_{protocol}_{len(self.test_case_table.rows)}",
                description="Automated test case",
                protocol=protocol,
                test_script=script
            )
            
            self.refresh_test_cases()
            QMessageBox.information(self, "Success", f"Test case created with ID: {test_case_id}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create test case: {str(e)}")

    def refresh_test_cases(self):
        # Clear existing items
        self.test_case_table.setRowCount(0)
        
        # Get test cases from database
        test_cases = self.test_framework.db.get_test_cases()
        
        for test_case in test_cases:
            row = self.test_case_table.rowCount()
            self.test_case_table.insertRow(row)
            
            self.test_case_table.setItem(row, 0, QTableWidgetItem(str(test_case['id'])))
            self.test_case_table.setItem(row, 1, QTableWidgetItem(test_case['name']))
            self.test_case_table.setItem(row, 2, QTableWidgetItem(test_case['protocol']))
            
            run_btn = QPushButton('Run')
            run_btn.clicked.connect(lambda: self.run_test(test_case['id']))
            self.test_case_table.setCellWidget(row, 3, run_btn)

    def run_test(self, test_case_id):
        try:
            result = self.test_framework.execute_test(test_case_id)
            self.update_results_table(result)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Test execution failed: {str(e)}")

    def run_selected_tests(self):
        selected_rows = self.test_case_table.selectedItems()
        test_ids = [int(self.test_case_table.item(row.row(), 0).text()) 
                   for row in selected_rows]
        
        try:
            results = self.test_framework.execute_test_suite(test_ids)
            for result in results:
                self.update_results_table(result)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Test suite execution failed: {str(e)}")

    def update_results_table(self, result):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(str(result['test_case']['id'])))
        self.results_table.setItem(row, 1, QTableWidgetItem(result['test_case']['name']))
        self.results_table.setItem(row, 2, QTableWidgetItem(result['status']))
        self.results_table.setItem(row, 3, QTableWidgetItem(f"{result['execution_time']:.2f}s"))
        self.results_table.setItem(row, 4, QTableWidgetItem(result.get('error_message', '')))

    def stop_execution(self):
        # Implement test execution stopping logic
        pass