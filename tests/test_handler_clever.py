import os
import shutil
import tempfile

from httmock import HTTMock

from dyntftpd.handlers.clever import CleverHandler

from . import TFTPServerTestCase


def get_http(url, request):
    return 'http'


class TestCleverHandler(TFTPServerTestCase):

    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        return super(TestCleverHandler, self).setUp(
            handler=CleverHandler, handler_args={
                'http': {
                    'cache_dir': self.cache_dir
                }
            })

    def test_forward_http(self):
        with HTTMock(get_http) as mock:
            self.get_file('http://www.download.tld/superfile')
            data, _ = self.recv()
            # \x00\x03 = data
            # \x00\x01 = block id 1
            self.assertEqual(data, '\x00\x03\x00\x01http')
            self.ack_n(1)

    def test_forward_fs(self):
        handle = open(os.path.join(self.tftp_root, 'test.txt'), 'w+')
        handle.write('fs')
        handle.flush()

        self.get_file('test.txt')
        data, _ = self.recv()
        # \x00\x03 = data
        # \x00\x01 = block id 1
        self.assertEqual(data, '\x00\x03\x00\x01fs')
        self.ack_n(1)

    def test_invalid_request(self):
        # Not enough arguments
        self.send('\x00\x01')
        data, _ = self.recv()
        self.assertTrue(data.startswith('\x00\x05\x00\x04'))
