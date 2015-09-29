import logging


__version__ = '0.4.1'

# Prevent message "No handlers could be found for logger "dyntftpd"" to be
# displayed
# Degrade on Python < 2.7
try:
    logging.getLogger(__name__).addHandler(logging.NullHandler())
except AttributeError:
    pass


from .server import TFTPServer

from .handlers.clever import CleverHandler
from .handlers.fs import FileSystemHandler
from .handlers.http import HTTPHandler
