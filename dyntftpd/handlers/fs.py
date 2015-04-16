import os

from . import TFTPUDPHandler, TFTPSession


class Session(TFTPSession):

    def __init__(self, tftp_handler, filename):
        """ Raise ValueError if trying to open a file up to the root folder.
        """
        server_root = os.path.abspath(tftp_handler.server.root)
        abs_path = os.path.abspath(os.path.join(server_root, filename))
        if os.path.commonprefix([abs_path, server_root]) != server_root:
            raise ValueError('Directory traversal prevented')
        super(Session, self).__init__(tftp_handler, abs_path)

    def load_file(self):
        return open(self.filename)

    def unload_file(self):
        self.handle.close()


class FileSystemHandler(TFTPUDPHandler):

    session_cls = Session
