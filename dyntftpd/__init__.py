__version__ = '0.4.1'

import logging

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

# Prevent message "No handlers could be found for logger "dyntftpd"" to be
# displayed
logging.getLogger(__name__).addHandler(NullHandler())

from .server import TFTPServer

from .handlers.clever import CleverHandler
from .handlers.fs import FileSystemHandler
from .handlers.http import HTTPHandler
