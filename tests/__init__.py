import shutil
import socket
import struct
import tempfile
import threading
import unittest

from dyntftpd.handlers.fs import FileSystemHandler
from dyntftpd.server import TFTPServer


class TFTPServerTestCase(unittest.TestCase):

    def setUp(self, handler=FileSystemHandler, handler_args=None):
        """ Starts an instance of TFTPServer and initializes a client socket.
        """
        self.tftp_root = tempfile.mkdtemp()

        self.server = TFTPServer(
            host='127.0.0.1', port=0, root=self.tftp_root,
            handler=handler, handler_args=handler_args
        )
        self.server.timeout = 0.001
        self.listen_ip, self.listen_port = self.server.socket.getsockname()

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, message):
        self.client_socket.sendto(message, (self.listen_ip, self.listen_port))

    def get_file(self, filename, mode='octet', options=None):
        request = '\x00\x01%s\x00%s\x00' % (filename, mode)
        if options is not None:
            request += ''.join([
                '%s\x00%s\x00' % (k, v) for k, v in options.items()
            ])
        return self.send(request)

    def recv(self, size=1024):
        data, addr = self.client_socket.recvfrom(size)
        return data, addr

    def ack(self, block_string):
        return self.send('\x00\x04' + block_string)

    def ack_n(self, block_id):
        return self.ack(struct.pack('>h', block_id))

    def tearDown(self):
        shutil.rmtree(self.tftp_root)
        self.server.shutdown()
        self.server.server_close()
