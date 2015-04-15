import os

from . import TFTPUDPHandler, TFTPSession


class Session(TFTPSession):

    def load_file(self):
        return open(self.filename)

    def unload_file(self):
        self.handle.close()


class FileSystemHandler(TFTPUDPHandler):

    session_cls = Session

    def sanitize_filename(self, filename):
        """ Raise if trying to open a file up to the root folder.
        """
        server_root = os.path.abspath(self.server.root)
        abs_path = os.path.abspath(os.path.join(server_root, filename))
        if os.path.commonprefix([abs_path, server_root]) != server_root:
            raise ValueError('Directory traversal prevented')
        return abs_path
