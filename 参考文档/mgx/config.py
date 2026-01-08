# config.py
class Config:
    # Database configuration
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'password'
    DB_NAME = 'softswitch_test'

    # Protocol configuration
    SIP_HOST = 'localhost'
    SIP_PORT = 5060
    ISUP_HOST = 'localhost'
    ISUP_PORT = 5061
    ISDN_HOST = 'localhost'
    ISDN_PORT = 5062

    # Test execution settings
    MAX_CONCURRENT_TESTS = 5
    TEST_TIMEOUT = 30  # seconds
    RETRY_COUNT = 3

    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'softswitch_test.log'

    # Report generation
    REPORT_TEMPLATE = 'templates/report_template.html'
    REPORT_OUTPUT_DIR = 'reports/'

    def __init__(self):
        # Initialize any dynamic configuration here
        pass

    def get_protocol_config(self, protocol):
        """Get configuration for specific protocol"""
        if protocol == 'SIP':
            return {
                'host': self.SIP_HOST,
                'port': self.SIP_PORT
            }
        elif protocol == 'ISUP':
            return {
                'host': self.ISUP_HOST,
                'port': self.ISUP_PORT
            }
        elif protocol == 'ISDN':
            return {
                'host': self.ISDN_HOST,
                'port': self.ISDN_PORT
            }
        else:
            raise ValueError(f"Unknown protocol: {protocol}")