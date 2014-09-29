import logging


__version__ = '0.1.1'

# Prevent message "No handlers could be found for logger "dyntftpd"" to be
# displayed if not logger is setup by the application.
logging.getLogger(__name__).addHandler(logging.NullHandler())


from .server import TFTPServer, FileSystemHandler
