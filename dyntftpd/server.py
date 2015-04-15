import SocketServer

from .handlers.clever import CleverHandler


class TFTPServer(SocketServer.UDPServer):
    """ Accepts the same arguments than SocketServer.UDPServer.

    Can also provide `handler_args`, a dictionary used by handlers to lookup
    their configuration.
    """

    timeout = 5

    def __init__(self, host='', port=69, root='/var/lib/tftpboot',
                 handler=CleverHandler, handler_args=None):

        self.sessions = {}
        self.root = root
        self.handler_args = handler_args or {}
        SocketServer.UDPServer.__init__(self, (host, port), handler)

    def serve_forever(self):
        """ The base method BaseServer.serve_forever doesn't handle timeouts. I
        guess this is not intended. Anyway, this ugly code is nothing else but
        more or less a copy/paste of the base class.
        """
        self._BaseServer__is_shut_down.clear()
        try:
            while not self._BaseServer__shutdown_request:
                self.handle_request()
        finally:
            self._BaseServer__shutdown_request = False
        self._BaseServer__is_shut_down.set()

    def handle_timeout(self):
        """ Called when the server didn't have a request for the last `timeout`
        seconds. If `self.seessions` isn't empty, it means clients asked for
        transferts but they disconnected before completing them. In this case,
        let's free the resources.
        """
        for client_address, session in self.sessions.items():
            session.unload_file()
            del self.sessions[client_address]
