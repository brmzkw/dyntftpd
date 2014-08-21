import errno
import logging
import os
import struct

import SocketServer


class TFTPUDPHandler(SocketServer.BaseRequestHandler):
    """ Mixin. Implementation of the TFTP protocol.

    http://tools.ietf.org/html/rfc1350
    """

    # opcodes
    OP_RRQ = 1
    OP_WRQ = 2
    OP_DATA = 3
    OP_ACK = 4
    OP_ERROR = 5

    # errors
    ERR_UNDEFINED = 0
    ERR_NOT_FOUND = 1
    ERR_PERM = 2
    ERR_DISK_FULL = 3
    ERR_ILLEGAL_OPERATION = 4
    ERR_UNKNOWN_TID = 5
    ERR_ALREADY_EXISTS = 6
    ERR_NO_SUCH_USER = 7

    def _log(self, level, msg, extra=None):
        """ Add client_ip to extra.
        """
        log_extra = {'client_ip': self.client_address[0]}
        if extra:
            log_extra.update(extra)
        logger = logging.getLogger(__name__)
        logger.log(level, msg, extra=log_extra)

    def handle(self):
        """ Extract header info and dispatch to handle_* methods.
        """
        data = self.request[0]
        opcode, = struct.unpack('!h', data[0:2])

        data = data[2:]  # skip opcode

        if opcode == self.OP_RRQ:
            filename = data[:data.index('\x00')]
            mode = data[len(filename) + 1:-1]  # skip leading and trailing \x00
            self.handle_rrq(filename, mode)

        elif opcode == self.OP_ACK:
            block_id, = struct.unpack('!h', data)
            self.handle_ack(block_id)

        else:
            self.send_error(
                self.ERR_ILLEGAL_OPERATION,
                'Opcode %d not handled by the server' % opcode
            )

    def handle_rrq(self, filename, mode):
        """ Handle READ requests.

        Create a new session.
        """
        self._log(logging.INFO, 'GET %s (%s)' % (filename, mode))

        if mode.lower() != 'octet':
            self.send_error(
                self.ERR_ILLEGAL_OPERATION,
                'Only octet mode is supported by the server'
            )
            return

        try:
            filename = self.sanitize_filename(filename)
        except ValueError as exc:
            self.send_error(self.ERR_PERM, str(exc))
            return

        try:
            handle = self.load_file(filename)
        except IOError as exc:
            # If ENOENT, consider the file is missing. Otherwise, consider we
            # don't have the permission to read it.
            err_msg = exc.strerror or str(exc)
            if exc.errno == errno.ENOENT:
                self.send_error(self.ERR_NOT_FOUND, err_msg)
            else:
                self.send_error(self.ERR_PERM, err_msg)
            return

        self.server.sessions[self.client_address] = TFTPSession(handle)
        self.send_data()

    def sanitize_filename(self, filename):
        """ Compute a filename that can be loaded by load_file. Make security
        checks to prevent path transversal.
        """
        raise NotImplementedError()

    def load_file(self, filename):
        """ Return a FILE like object.
        """
        raise NotImplementedError()

    def handle_ack(self, block_id):
        """ Client has aknowledged a block id. Can be a retransmission or the
        next packet to send.
        """
        self._log(logging.DEBUG, 'ACK (block %s)' % block_id)
        session = self.server.sessions.get(self.client_address)

        # If the ACK does not correspond to a read request
        if not session:
            return

        # Last packet was received
        if block_id == session.block_id + 1:

            # Final ACK from the client, kill the sesssion
            if session.last_read_is_eof:
                self._log(
                    logging.INFO,
                    'Transfer of %s successful' % session.handle.name
                )
                del self.server.sessions[self.client_address]
                return

            # Next packet
            session.block_id += 1

        # Send the next packet, or retransmit the last packet if there was an
        # error
        self.send_data()

    def send_data(self):
        """ Send the next data packet to the client.
        """
        session = self.server.sessions[self.client_address]
        session.handle.seek(session.block_id * 512)
        data = session.handle.read(512)
        session.last_read_is_eof = len(data) < 512

        packed = struct.pack('!hh', self.OP_DATA, session.block_id + 1)
        packed += data

        socket = self.request[1]
        socket.sendto(packed, self.client_address)

    def send_error(self, error_code, error_msg):
        """ Send error packet to the client.
        """
        self._log(logging.ERROR, error_msg)
        socket = self.request[1]
        packed = struct.pack('!hh', self.OP_ERROR, error_code)
        packed += error_msg + '\x00'
        socket.sendto(packed, self.client_address)


class TFTPSession(object):

    def __init__(self, handle):
        self.block_id = 0
        self.handle = handle
        self.last_read_is_eof = False


class FileSystemHandler(TFTPUDPHandler):

    def sanitize_filename(self, filename):
        """ Raise if trying to open a file up to the root folder.
        """
        server_root = self.server.root
        abs_path = os.path.abspath(os.path.join(server_root, filename))
        if os.path.commonprefix([abs_path, server_root]) != server_root:
            raise ValueError('Directory trasversal prevented')
        return abs_path

    def load_file(self, filename):
        return open(filename)


class TFTPServer(SocketServer.UDPServer):

    def __init__(self, host='', port=69, root='/var/lib/tftboot',
                 handler=FileSystemHandler):

        self.sessions = {}
        self.root = root
        SocketServer.UDPServer.__init__(self, (host, port), handler)
