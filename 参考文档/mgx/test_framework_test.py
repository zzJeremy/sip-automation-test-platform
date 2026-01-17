# tests/test_framework_test.py
import unittest
from unittest.mock import MagicMock, patch
from core.test_framework import TestFramework, TestCase
from db.database import Database

class TestFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock(spec=Database)
        self.test_framework = TestFramework(self.mock_db)

    def test_create_test_case(self):
        # Arrange
        test_name = "Test_SIP_1"
        test_description = "Test Description"
        test_protocol = "SIP"
        test_script = "test script content"
        expected_id = 1
        
        self.mock_db.add_test_case.return_value = expected_id

        # Act
        test_case_id = self.test_framework.create_test_case(
            test_name, test_description, test_protocol, test_script
        )

        # Assert
        self.assertEqual(test_case_id, expected_id)
        self.mock_db.add_test_case.assert_called_once_with(
            test_name, test_description, test_protocol, test_script
        )

    def test_execute_test(self):
        # Arrange
        test_case_id = 1
        test_case = {
            'id': test_case_id,
            'name': 'Test_SIP_1',
            'protocol': 'SIP',
            'test_script': 'test script'
        }
        self.mock_db.get_test_case.return_value = test_case

        # Act
        result = self.test_framework.execute_test(test_case_id)

        # Assert
        self.assertIn('test_case', result)
        self.assertIn('status', result)
        self.assertIn('execution_time', result)
        self.mock_db.get_test_case.assert_called_once_with(test_case_id)
        self.mock_db.add_test_result.assert_called_once()

    def test_execute_test_suite(self):
        # Arrange
        test_case_ids = [1, 2, 3]
        test_cases = [
            {'id': 1, 'protocol': 'SIP', 'test_script': 'script1'},
            {'id': 2, 'protocol': 'ISUP', 'test_script': 'script2'},
            {'id': 3, 'protocol': 'ISDN', 'test_script': 'script3'}
        ]
        self.mock_db.get_test_case.side_effect = test_cases

        # Act
        results = self.test_framework.execute_test_suite(test_case_ids)

        # Assert
        self.assertEqual(len(results), len(test_case_ids))
        self.assertEqual(self.mock_db.get_test_case.call_count, len(test_case_ids))
        self.assertEqual(self.mock_db.add_test_result.call_count, len(test_case_ids))

if __name__ == '__main__':
    unittest.main()