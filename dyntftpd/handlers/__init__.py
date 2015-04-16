import errno
import logging
import os
import struct

import SocketServer


logger = logging.getLogger(__name__)


class TFTPSession(object):
    """ Represents a file transfert for a client.
    """
    def __init__(self, tftp_handler, filename):
        self.tftp_handler = tftp_handler
        self.filename = filename
        self.handle = None
        self.block_id = 0
        self.last_read_is_eof = False
        self.blksize = 512

    def load_file(self):
        raise NotImplementedError

    def unload_file(self):
        raise NotImplementedError


class TFTPUDPHandler(SocketServer.BaseRequestHandler):
    """ Mixin. Implementation of the TFTP protocol.

    http://tools.ietf.org/html/rfc1350
    http://tools.ietf.org/html/rfc1782
    """

    # opcodes
    OP_RRQ = 1
    OP_WRQ = 2
    OP_DATA = 3
    OP_ACK = 4
    OP_ERROR = 5
    OP_OACK = 6

    # errors
    ERR_UNDEFINED = 0
    ERR_NOT_FOUND = 1
    ERR_PERM = 2
    ERR_DISK_FULL = 3
    ERR_ILLEGAL_OPERATION = 4
    ERR_UNKNOWN_TID = 5
    ERR_ALREADY_EXISTS = 6
    ERR_NO_SUCH_USER = 7

    session_cls = None

    def make_session(self, filename):
        return self.session_cls(self, filename)

    def _log(self, level, msg, extra=None, exc_info=False):
        """ Add client_ip to extra.
        """
        log_extra = {'client_ip': self.client_address[0]}
        if extra:
            log_extra.update(extra)
        logger.log(level, msg, extra=log_extra, exc_info=exc_info)

    def get_current_session(self):
        """ Gets the client's session, or returns None.
        """
        return self.server.sessions.get(self.client_address)

    def set_current_session(self, session):
        """ Sets the session for this client to `session`.
        """
        self.server.sessions[self.client_address] = session

    def cleanup_session(self):
        """ Deletes the current session, if exists.

        Further calls to get_current_session will return None.
        """
        session = self.get_current_session()
        if session:
            session.unload_file()

        try:
            del self.server.sessions[self.client_address]
        except KeyError:
            pass

    def handle(self):
        """ Called when data are received. Extract header info and dispatch to
        handle_* methods.
        """
        data = self.request[0]
        opcode, = struct.unpack('!h', data[0:2])

        data = data[2:]  # skip opcode

        if opcode == self.OP_RRQ:
            args = data.split('\x00')

            if args[-1] != '':
                return self.send_error(
                    self.ERR_ILLEGAL_OPERATION,
                    'Final argument should end with a \\0'
                )
            args = args[:-1]  # skip final \0

            if len(args) < 2:
                return self.send_error(
                    self.ERR_ILLEGAL_OPERATION,
                    "Filename and mode required"
                )

            filename, mode = args[0], args[1]
            options = args[2:]

            # options must be a list like: [optname1, optvalue1, ..., optnameN,
            # optvalueN)
            if len(options) % 2:
                return self.send_error(
                    self.ERR_ILLEGAL_OPERATION,
                    "Malformed options"
                )

            # transform options to a dict
            options = dict(options[i:i+2] for i in xrange(0, len(options), 2))

            self.handle_rrq(filename, mode, options)

        elif opcode == self.OP_ACK:
            block_id, = struct.unpack('!h', data)
            self.handle_ack(block_id)

        else:
            return self.send_error(
                self.ERR_ILLEGAL_OPERATION,
                'Opcode %d not handled by the server' % opcode
            )

    def handle_rrq(self, filename, mode, options):
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
            session = self.make_session(filename)
        except ValueError as exc:  # if filename is invalid
            self.send_error(self.ERR_PERM, str(exc))
            return

        try:
            session.handle = session.load_file()
        except IOError as exc:
            # If ENOENT, consider the file is missing. Otherwise, consider we
            # don't have the permission to read it.
            err_msg = exc.strerror or str(exc)
            if exc.errno == errno.ENOENT:
                self.send_error(
                    self.ERR_NOT_FOUND, '%s (%s)' % (err_msg, filename)
                )
            else:
                self.send_error(
                    self.ERR_PERM, '%s (%s)' % (err_msg, filename)
                )
            return
        # The file cannot be loaded for any (critical) reason. Log the
        # traceback.
        except Exception as exc:
            self._log(logging.ERROR, 'Internal error', exc_info=True)
            self.send_error(self.ERR_UNDEFINED, 'Internal error')
            return

        self.set_current_session(session)

        # If there is a supported option, return a OACK, otherwise return the
        # first packet.
        # For now, only 'blksize' is supported.
        blksize = options.get('blksize')

        # Set the block size and return a OACK
        if blksize:
            try:
                session.blksize = int(blksize)
            except ValueError:  # not an int
                return self.send_error(
                    self.ERR_ILLEGAL_OPERATION, 'Bad option value'
                )
            return self.send_oack(blksize=blksize)

        # No options, return the first part of the file
        self.send_data()

    def handle_ack(self, block_id):
        """ Client has aknowledged a block id. Can be a retransmission or the
        next packet to send.
        """
        self._log(logging.DEBUG, 'ACK (block %s)' % block_id)
        session = self.get_current_session()

        # If the ACK does not correspond to a read request
        if not session:
            return

        # Last packet was received
        if block_id == session.block_id + 1:

            # Final ACK from the client, kill the session
            if session.last_read_is_eof:
                self._log(
                    logging.INFO,
                    'Transfer of %s successful' % session.filename
                )
                self.cleanup_session()
                return

            # Next packet
            session.block_id += 1

        # Send the next packet, or retransmit the last packet if there was an
        # error
        self.send_data()

    def send_oack(self, **options):
        """ Send options acknowledgement.
        """
        packed = struct.pack('!h', self.OP_OACK)
        for key, value in options.iteritems():
            packed += key + '\x00' + value + '\x00'

        socket = self.request[1]
        socket.sendto(packed, self.client_address)

    def send_data(self):
        """ Send the next data packet to the client.
        """
        session = self.get_current_session()
        session.handle.seek(session.block_id * session.blksize)
        data = session.handle.read(session.blksize)
        session.last_read_is_eof = len(data) < session.blksize

        try:
            packed = struct.pack('!hh', self.OP_DATA, session.block_id + 1)
        except struct.error as exc:
            self.send_error(
                self.ERR_UNDEFINED,
                'File too big for this blksize. block id overflows.'
            )
            return

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
        self.cleanup_session()
