# tests/protocol_handlers_test.py
import unittest
from unittest.mock import MagicMock, patch
from core.protocol_handlers import SIPHandler, ISUPHandler, ISDNHandler

class SIPHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = SIPHandler()

    @patch('socket.socket')
    def test_connect(self, mock_socket):
        # Arrange
        host = "localhost"
        port = 5060
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Act
        self.handler.connect(host, port)

        # Assert
        mock_socket.assert_called_once()
        mock_socket_instance.bind.assert_called_once_with((host, port))
        self.assertIsNotNone(self.handler.socket)

    def test_disconnect(self):
        # Arrange
        self.handler.socket = MagicMock()

        # Act
        self.handler.disconnect()

        # Assert
        self.handler.socket.close.assert_called_once()
        self.assertIsNone(self.handler.socket)

    def test_execute_test(self):
        # Arrange
        test_script = "TEST SCRIPT"

        # Act
        result = self.handler.execute_test(test_script)

        # Assert
        self.assertTrue(result)

class ISUPHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = ISUPHandler()

    @patch('socket.socket')
    def test_connect(self, mock_socket):
        # Arrange
        host = "localhost"
        port = 5061
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Act
        self.handler.connect(host, port)

        # Assert
        mock_socket.assert_called_once()
        mock_socket_instance.connect.assert_called_once_with((host, port))
        self.assertIsNotNone(self.handler.socket)

    def test_disconnect(self):
        # Arrange
        self.handler.socket = MagicMock()

        # Act
        self.handler.disconnect()

        # Assert
        self.handler.socket.close.assert_called_once()
        self.assertIsNone(self.handler.socket)

class ISDNHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = ISDNHandler()

    @patch('socket.socket')
    def test_connect(self, mock_socket):
        # Arrange
        host = "localhost"
        port = 5062
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Act
        self.handler.connect(host, port)

        # Assert
        mock_socket.assert_called_once()
        mock_socket_instance.connect.assert_called_once_with((host, port))
        self.assertIsNotNone(self.handler.socket)

    def test_disconnect(self):
        # Arrange
        self.handler.socket = MagicMock()

        # Act
        self.handler.disconnect()

        # Assert
        self.handler.socket.close.assert_called_once()
        self.assertIsNone(self.handler.socket)

if __name__ == '__main__':
    unittest.main()