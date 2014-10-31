import SocketServer
import os
import shutil
import socket
import struct
import tempfile
import threading
import unittest

from dyntftpd.handlers import TFTPUDPHandler
from dyntftpd.handlers.fs import FileSystemHandler
from dyntftpd.server import TFTPServer


class ThreadedTFTPServer(SocketServer.ThreadingMixIn, TFTPServer):
    pass


class TFTPServerTestCase(unittest.TestCase):

    def setUp(self, handler=FileSystemHandler):
        """ Starts an instance of TFTPServer and initializes a client socket.
        """
        self.tftp_root = tempfile.mkdtemp()

        self.server = ThreadedTFTPServer(
            host='127.0.0.1', port=0, root=self.tftp_root, handler=handler
        )
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


class TestFileSystemHandler(TFTPServerTestCase):

    def test_invalid_request(self):
        # Missing trailing \x00
        self.send('\x00\x01filename\x00octet')
        data, _ = self.recv()
        self.assertTrue(data.startswith('\x00\x05\x00\x04'))

        # Not enough arguments
        self.send('\x00\x01')
        data, _ = self.recv()
        self.assertTrue(data.startswith('\x00\x05\x00\x04'))

        self.send('\x00\x01filename\x00')
        data, _ = self.recv()
        self.assertTrue(data.startswith('\x00\x05\x00\x04'))

    def test_non_existing(self):
        self.get_file('invalid')
        data, _ = self.recv()
        # \x00\x05 = error
        # \x00\x01 = no such file
        self.assertTrue(data.startswith('\x00\x05\x00\x01'))

    def test_non_octet(self):
        """ Currently, the server only supports ascii transfers.
        """
        self.get_file('yo.txt', mode='ascii')
        data, _ = self.recv()
        # \x00\x05 = error
        # \x00\x04 = illegal operation
        self.assertTrue(data.startswith('\x00\x05\x00\x04'))

    def test_empty_file(self):
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.close()

        self.get_file('test.txt')
        data, _ = self.recv()
        # \x00\x03 = data
        # \x00\x01 = block id 1
        self.assertEqual(data, '\x00\x03\x00\x01')
        self.ack_n(1)

    def test_small_file(self):
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.write('hello world')
        handle.flush()

        self.get_file('test.txt')
        data, _ = self.recv()
        # \x00\x03 = data
        # \x00\x01 = block id 1
        self.assertEqual(data, '\x00\x03\x00\x01hello world')
        self.ack_n(1)

    def test_options(self):
        """ Ensure blksize can be given, and other options are ignored.

        http://tools.ietf.org/html/rfc1782
        """
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.write('hello world')
        handle.flush()

        self.get_file('test.txt', options={'blksize': 1024, 'timeout': 5})
        data, _ = self.recv()
        # \x00\x06 = OACK
        self.assertEqual(data, '\x00\x06blksize\x001024\x00')

    def test_big_file(self):
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.write('A' * 512)
        handle.write('B' * 512)
        handle.write('C' * 32)
        handle.flush()

        self.get_file('test.txt')
        data, _ = self.recv()
        # \x00\x03 = data
        # \x00\x01 = block id 1
        self.assertEqual(len(data), 516)
        self.assertEqual(data, '\x00\x03\x00\x01' + 'A' * 512)
        self.ack_n(1)

        data, _ = self.recv()
        self.assertEqual(len(data), 516)
        self.assertEqual(data, '\x00\x03\x00\x02' + 'B' * 512)
        self.ack_n(2)

        data, _ = self.recv()
        self.assertEqual(len(data), 36)
        self.assertEqual(data, '\x00\x03\x00\x03' + 'C' * 32)
        self.ack_n(3)

    def test_big_file_with_blksize(self):
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.write('A' * 512)
        handle.write('B' * 512)
        handle.write('C' * 32)
        handle.flush()

        self.get_file('test.txt', options={'blksize': 1024})

        # \x00\x06 = OACK
        data, _ = self.recv()
        self.assertEqual(data, '\x00\x06blksize\x001024\x00')
        self.ack_n(0)

        data, _ = self.recv(size=4096)
        self.assertEqual(len(data), 1024 + 4)
        # \x00\x03 = data
        # \x00\x01 = block id 1
        self.assertEqual(data, '\x00\x03\x00\x01' + 'A' * 512 + 'B' * 512)
        self.ack_n(1)

        data, _ = self.recv(size=4096)
        self.assertEqual(len(data), 32 + 4)
        # \x00\x03 = data
        # \x00\x01 = block id 2
        self.assertEqual(data, '\x00\x03\x00\x02' + 'C' * 32)

    def test_directory_transversal(self):
        self.get_file('../../yo.txt')
        data, _ = self.recv()
        # \x00\x05 = error
        # \x00\x04 = permission denied
        self.assertTrue(data.startswith('\x00\x05\x00\x02'))

    def test_permission_denied(self):
        filename = os.path.join(self.tftp_root, 'test.txt')
        handle = open(filename, 'w+')
        handle.write('hello world')
        os.chmod(filename, 0000)
        handle.flush()

        self.get_file('test.txt')
        data, _ = self.recv()
        # \x00\x05 = error
        # \x00\x04 = permission denied
        self.assertTrue(data.startswith('\x00\x05\x00\x02'))

    def test_retransmission(self):
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.write('A' * 512)
        handle.write('B' * 512)
        handle.flush()

        self.get_file('test.txt')
        data, _ = self.recv()
        # \x00\x03 = data
        # \x00\x01 = block id 1
        self.assertEqual(len(data), 516)
        self.assertEqual(data, '\x00\x03\x00\x01' + 'A' * 512)
        self.ack_n(1)

        data, _ = self.recv()
        self.assertEqual(len(data), 516)
        self.assertEqual(data, '\x00\x03\x00\x02' + 'B' * 512)

        # Retransmit. Aknowledge the last packet.
        self.ack_n(1)
        data, _ = self.recv()
        self.assertEqual(len(data), 516)
        self.assertEqual(data, '\x00\x03\x00\x02' + 'B' * 512)


class CustomHandler(TFTPUDPHandler):

    def sanitize_filename(self, filename):
        return filename

    def load_file(self, filename):
        raise OSError('xxx')


class TestCustomHandler(TFTPServerTestCase):

    def setUp(self):
        return super(TestCustomHandler, self).setUp(handler=CustomHandler)

    def test_load_file_failing(self):
        self.get_file('whatever')
        data, _ = self.recv()
        # \x00\x05 = error
        # \x00\x00 = undefined
        self.assertEqual(data, '\x00\x05\x00\x00Internal error\x00')
