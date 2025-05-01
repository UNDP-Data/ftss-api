#!/usr/bin/env python
"""
A simple script to test Bugsnag integration.
"""

import os
import sys
import time
import bugsnag
from src.bugsnag_config import configure_bugsnag, setup_bugsnag_logging

def test_bugsnag():
    """Test Bugsnag integration with various error types."""
    print("Configuring Bugsnag...")
    configure_bugsnag()
    setup_bugsnag_logging()
    
    # Send a simple test error
    print("Sending a test error to Bugsnag...")
    bugsnag.notify(
        Exception("Test error from test_bugsnag.py"),
        metadata={
            "test_data": {
                "timestamp": time.time(),
                "environment": os.environ.get("ENVIRONMENT", "development"),
                "python_version": sys.version
            }
        }
    )
    print("Test error sent. Check your Bugsnag dashboard.")
    
    # Test error with breadcrumbs
    print("Testing error with breadcrumbs...")
    bugsnag.leave_breadcrumb("Started test process", metadata={"step": 1})
    bugsnag.leave_breadcrumb("Processing data", metadata={"step": 2, "data_size": 1024})
    bugsnag.leave_breadcrumb("Completed processing", metadata={"step": 3, "status": "success"})
    
    try:
        # Simulate a real error
        result = 1 / 0
    except Exception as e:
        print("Sending a division by zero error to Bugsnag...")
        bugsnag.notify(
            e,
            metadata={
                "error_context": {
                    "operation": "division",
                    "divisor": 0
                }
            }
        )
    
    print("Test completed. Please check your Bugsnag dashboard for the reported errors.")

if __name__ == "__main__":
    test_bugsnag() 