import logging
from logging.config import dictConfig
import os
logging_config = dict(
    version=1,
    disable_existing_loggers=False,
    formatters={
        'f': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
        }
    },
    handlers={
        'debug_file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'f',
            'filename': os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'debug.log')),
            'level': logging.DEBUG
        },
        'info_file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'f',
            'filename': os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'info.log')),
            'level': logging.INFO
        },
        'err_file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'f',
            'filename': os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'error.log')),
            'level': logging.ERROR
        },
    },
    root={
        'handlers': ['err_file_handler', 'info_file_handler', 'debug_file_handler'],
        'level': logging.DEBUG,
    },
)

dictConfig(logging_config)
