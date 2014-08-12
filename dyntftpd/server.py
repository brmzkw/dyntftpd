import errno
import os
import struct

import SocketServer


class TFTPUDPHandler(SocketServer.BaseRequestHandler):
    """ http://tools.ietf.org/html/rfc1350
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

    def handle(self):
        """ Extract header info and dispatch to handle_* methods.
        """
        data, socket = self.request
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
        if mode.lower() != 'octet':
            self.send_error(
                self.ERR_ILLEGAL_OPERATION,
                'Only octet mode is supported by the server'
            )
            return

        try:
            filename = self.server.find_file(filename)
        except ValueError as exc:
            self.send_error(self.ERR_PERM, str(exc))
            return

        try:
            handle = open(filename)
        except IOError as exc:
            err = self.ERR_NOT_FOUND if exc.errno == errno.ENOENT else \
                self.ERR_PERM
            self.send_error(err, exc.strerror)
            return

        self.server.sessions[self.client_address] = TFTPSession(handle)
        self.send_data()

    def handle_ack(self, block_id):
        """ Client has aknowledged a block id. Can be a retransmission or the
        next packet to send.
        """
        session = self.server.sessions.get(self.client_address)

        # If the ACK does not correspond to a read request
        if not session:
            return

        # Last packet was received
        if block_id == session.block_id + 1:

            # Final ACK from the client, kill the sesssion
            if session.last_read_is_eof:
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
        socket = self.request[1]
        packed = struct.pack('!hh', self.OP_ERROR, error_code)
        packed += error_msg + '\x00'
        socket.sendto(packed, self.client_address)


class TFTPSession(object):

    def __init__(self, handle):
        self.block_id = 0
        self.handle = handle
        self.last_read_is_eof = False


class TFTPServer(SocketServer.UDPServer):

    handler = TFTPUDPHandler

    def __init__(self, host='localhost', port=69, root='/tftboot'):
        self.sessions = {}
        self.root = root
        SocketServer.UDPServer.__init__(self, (host, port), self.handler)

    def find_file(self, filename):
        """ Find the absolute path of `filename` located in root.
        """
        abs_path = os.path.abspath(os.path.join(self.root, filename))
        if os.path.commonprefix([abs_path, self.root]) != self.root:
            raise ValueError('Directory trasversal prevented')
        return abs_path


def main():
    tftp_server = TFTPServer('localhost', 9999, root='/tmp')
    tftp_server.serve_forever()
