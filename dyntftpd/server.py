import SocketServer

from .handlers.fs import FileSystemHandler


class TFTPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):

    def __init__(self, host='', port=69, root='/var/lib/tftpboot',
                 handler=FileSystemHandler):

        self.sessions = {}
        self.root = root
        SocketServer.UDPServer.__init__(self, (host, port), handler)
