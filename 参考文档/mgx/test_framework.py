# core/test_framework.py
import unittest
import time
import logging
from typing import List, Dict, Any
from db.database import Database
from core.protocol_handlers import SIPHandler, ISUPHandler, ISDNHandler

class TestCase:
    def __init__(self, name: str, description: str, protocol: str, test_script: str):
        self.name = name
        self.description = description
        self.protocol = protocol
        self.test_script = test_script
        self.result = None
        self.error_message = None
        self.execution_time = 0

class TestFramework:
    def __init__(self, database: Database):
        self.db = database
        self.protocol_handlers = {
            'SIP': SIPHandler(),
            'ISUP': ISUPHandler(),
            'ISDN': ISDNHandler()
        }
        self.logger = logging.getLogger(__name__)

    def create_test_case(self, name: str, description: str, protocol: str, test_script: str) -> int:
        """Create a new test case and store it in the database."""
        try:
            test_case_id = self.db.add_test_case(name, description, protocol, test_script)
            self.logger.info(f"Created test case: {name}")
            return test_case_id
        except Exception as e:
            self.logger.error(f"Failed to create test case: {str(e)}")
            raise

    def execute_test(self, test_case_id: int) -> Dict[str, Any]:
        """Execute a single test case."""
        start_time = time.time()
        test_case = self.db.get_test_case(test_case_id)
        
        if not test_case:
            raise ValueError(f"Test case {test_case_id} not found")

        try:
            # Get appropriate protocol handler
            handler = self.protocol_handlers.get(test_case['protocol'])
            if not handler:
                raise ValueError(f"Unsupported protocol: {test_case['protocol']}")

            # Execute the test
            result = handler.execute_test(test_case['test_script'])
            status = 'PASS' if result else 'FAIL'
            error_message = None
            
        except Exception as e:
            status = 'ERROR'
            error_message = str(e)
            self.logger.error(f"Test execution error: {error_message}")

        execution_time = time.time() - start_time
        
        # Store result in database
        self.db.add_test_result(
            test_case_id=test_case_id,
            status=status,
            execution_time=execution_time,
            error_message=error_message
        )

        return {
            'test_case': test_case,
            'status': status,
            'execution_time': execution_time,
            'error_message': error_message
        }

    def execute_test_suite(self, test_case_ids: List[int]) -> List[Dict[str, Any]]:
        """Execute multiple test cases as a suite."""
        results = []
        for test_id in test_case_ids:
            try:
                result = self.execute_test(test_id)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to execute test {test_id}: {str(e)}")
                results.append({
                    'test_case_id': test_id,
                    'status': 'ERROR',
                    'error_message': str(e)
                })
        return results

    def get_test_results(self, test_case_id: int = None) -> List[Dict[str, Any]]:
        """Retrieve test results from the database."""
        return self.db.get_test_results(test_case_id)