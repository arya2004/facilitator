import logging.config
import os

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'app.services.openai_service': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'app': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
}

def setup_logging():
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Apply logging configuration
    logging.config.dictConfig(LOGGING_CONFIG)

    # Set log level from environment variable if provided
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    try:
        numeric_level = getattr(logging, log_level)
        logging.getLogger().setLevel(numeric_level)
        logging.getLogger('app').setLevel(numeric_level)
        logging.getLogger('app.services.openai_service').setLevel(logging.DEBUG)
    except AttributeError:
        logging.warning(f"Invalid LOG_LEVEL '{log_level}', using INFO")
        logging.getLogger().setLevel(logging.INFO)