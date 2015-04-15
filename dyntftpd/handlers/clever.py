from .fs import FileSystemHandler, Session as FSSession
from .http import HTTPHandler, Session as HTTPSession


def for_http_handler(filename):
    """ Returns True if `filename` is a link.
    """
    return filename.startswith('http://') or filename.startswith('https://')


class CleverHandler(FileSystemHandler, HTTPHandler):

    def sanitize_filename(self, filename):
        """ Forwards to HTTPHandler or to FileSystemHandler.
        """
        maybe_url = HTTPHandler.sanitize_filename(self, filename)
        if for_http_handler(maybe_url):
            return maybe_url
        return FileSystemHandler.sanitize_filename(self, filename)

    def make_session(self, filename):
        if for_http_handler(filename):
            return HTTPSession(self, filename)
        return FSSession(self, filename)
