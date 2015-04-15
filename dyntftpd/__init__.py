import logging


__version__ = '0.4.0'

# Prevent message "No handlers could be found for logger "dyntftpd"" to be
# displayed
logging.getLogger(__name__).addHandler(logging.NullHandler())


from .server import TFTPServer, FileSystemHandler
