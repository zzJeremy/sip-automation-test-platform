# Softswitch System Automated Testing Platform

A comprehensive automated testing platform for softswitch systems, supporting SIP, ISUP, and ISDN protocols.

## Features

- Test case management with database storage
- Protocol simulation for SIP, ISUP, and ISDN
- Concurrent test execution support
- Real-time test result monitoring
- Automated test report generation
- PyQt5-based graphical user interface

## Prerequisites

- Python 3.8 or higher
- MySQL Server
- PyQt5 
- Network connectivity for protocol testing

## Installation

1. Clone the repository:


2. Create and activate a virtual environment:


3. Install dependencies:


4. Configure MySQL database:
   - Create a new database named `softswitch_test`
   - Update database credentials in `config.py`

## Configuration

Edit `config.py` to configure:
- Database connection parameters
- Protocol endpoints (SIP, ISUP, ISDN)
- Test execution settings
- Logging configuration
- Report generation settings

## Usage

1. Start the application:


2. Using the GUI:
   - Create test cases using the Test Case Management tab
   - Execute tests individually or as a suite
   - Monitor test execution in real-time
   - View and export test results

## Test Case Development

Test cases can be written in a simple script format:
