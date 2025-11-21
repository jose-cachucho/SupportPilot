"""
Logging Utility for SupportPilot

This module configures a centralized logging system that writes to both
console and file. It supports observability by capturing:
- User inputs
- Agent responses
- Tool calls and outputs
- System errors

The log file is stored in the 'logs/' directory and follows a structured
format suitable for analysis and debugging.

Usage:
    from src.utils.logger import setup_logger
    
    logger = setup_logger("MyModule")
    logger.info("Operation successful")
    logger.error("An error occurred")

Author: SupportPilot Team
"""

import logging
import os
from typing import Optional


def setup_logger(name: str = "SupportPilot") -> logging.Logger:
    """
    Configures and returns a logger with file and console handlers.
    
    The logger writes to 'logs/support_pilot.log' with timestamps,
    log levels, and module names for full traceability.
    
    Args:
        name (str): The logger name (typically the module name).
                    Defaults to "SupportPilot".
    
    Returns:
        logging.Logger: Configured logger instance ready for use.
    
    Features:
        - Automatic log directory creation
        - UTF-8 encoding for international character support
        - Prevents duplicate handlers on re-initialization
        - Structured format: timestamp - [level] - name - message
    
    Example:
        >>> logger = setup_logger("TicketAgent")
        >>> logger.info("Ticket created successfully")
        2025-01-15 10:30:45 - [INFO] - TicketAgent - Ticket created successfully
    """
    # 1. Ensure the 'logs' directory exists in the project root
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 2. Get or create logger instance
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # Capture INFO level and above
    
    # 3. Prevent duplicate handlers if logger already configured
    if logger.hasHandlers():
        return logger
    
    # 4. Define log message format (timestamp - level - name - message)
    formatter = logging.Formatter(
        fmt='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 5. Configure file handler (writes to logs/support_pilot.log)
    log_file_path = os.path.join(log_dir, "support_pilot.log")
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 6. Attach handler to logger
    logger.addHandler(file_handler)
    
    # 7. Confirmation message (helps verify logger initialization)
    print(f"📋 [Logger] Configured. Output file: {log_file_path}")
    
    return logger