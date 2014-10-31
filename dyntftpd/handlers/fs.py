import os

from . import TFTPUDPHandler


class FileSystemHandler(TFTPUDPHandler):

    def sanitize_filename(self, filename):
        """ Raise if trying to open a file up to the root folder.
        """
        server_root = os.path.abspath(self.server.root)
        abs_path = os.path.abspath(os.path.join(server_root, filename))
        if os.path.commonprefix([abs_path, server_root]) != server_root:
            raise ValueError('Directory traversal prevented')
        return abs_path

    def load_file(self, filename):
        return open(filename)
