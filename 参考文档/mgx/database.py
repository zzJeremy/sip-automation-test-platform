# db/database.py
import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Any
import logging

class Database:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None
        self.connect()
        self._create_tables()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**self.config)
            logging.info("Database connection successful")
        except Error as e:
            logging.error(f"Error connecting to database: {e}")
            raise

    def _create_tables(self):
        cursor = self.connection.cursor()
        
        # Test Cases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                protocol ENUM('SIP', 'ISUP', 'ISDN'),
                test_script TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Test Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                test_case_id INT,
                status ENUM('PASS', 'FAIL', 'ERROR') NOT NULL,
                execution_time FLOAT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_case_id) REFERENCES test_cases(id)
            )
        """)
        
        self.connection.commit()

    def add_test_case(self, name: str, description: str, protocol: str, test_script: str) -> int:
        cursor = self.connection.cursor()
        query = """
            INSERT INTO test_cases (name, description, protocol, test_script)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (name, description, protocol, test_script))
        self.connection.commit()
        return cursor.lastrowid

    def get_test_case(self, test_case_id: int) -> Dict[str, Any]:
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM test_cases WHERE id = %s", (test_case_id,))
        return cursor.fetchone()

    def add_test_result(self, test_case_id: int, status: str, execution_time: float, error_message: str = None):
        cursor = self.connection.cursor()
        query = """
            INSERT INTO test_results (test_case_id, status, execution_time, error_message)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (test_case_id, status, execution_time, error_message))
        self.connection.commit()

    def get_test_results(self, test_case_id: int = None) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor(dictionary=True)
        if test_case_id:
            cursor.execute("SELECT * FROM test_results WHERE test_case_id = %s", (test_case_id,))
        else:
            cursor.execute("SELECT * FROM test_results")
        return cursor.fetchall()

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()