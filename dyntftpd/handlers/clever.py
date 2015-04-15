from .fs import FileSystemHandler, Session as FSSession
from .http import HTTPHandler, Session as HTTPSession


def for_http_handler(filename):
    """ Returns True if `filename` is a link.
    """
    return filename.startswith('http://') or filename.startswith('https://')


class Session(object):
    """ Forward file loading/unloading to FSSession or HTTPSession.
    """
    def __init__(self, tftp_handler, filename):
        if for_http_handler(filename):
            self._session = HTTPSession(tftp_handler, filename)
        else:
            self._session = FSSession(tftp_handler, filename)

    def __getattr__(self, name):
        return getattr(self._session, name)


class CleverHandler(FileSystemHandler, HTTPHandler):

    session_cls = Session

    def sanitize_filename(self, filename):
        """ Forwards to HTTPHandler or to FileSystemHandler.
        """
        maybe_url = HTTPHandler.sanitize_filename(self, filename)

        if for_http_handler(maybe_url):
            return maybe_url

        return FileSystemHandler.sanitize_filename(self, filename)
