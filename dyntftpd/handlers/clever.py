import urllib

from . import TFTPUDPHandler
from .fs import FileSystemHandler, Session as FSSession
from .http import HTTPHandler, Session as HTTPSession


class CleverHandler(TFTPUDPHandler):

    def make_session(self, filename):
        maybe_url = urllib.unquote(filename)

        if (
            maybe_url.startswith('http://') or
            maybe_url.startswith('https://')
        ):
            return HTTPSession(self, filename)
        return FSSession(self, filename)
