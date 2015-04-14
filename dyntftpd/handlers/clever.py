from .fs import FileSystemHandler
from .http import HTTPHandler


class CleverHandler(FileSystemHandler, HTTPHandler):
    """ Forward requests to FileSystemHandler or HTTPHandler depending on the
    request.
    """

    def for_http_handler(self, filename):
        """ Returns a boolean, depending on if `filename` is a HTTP link or
        not.
        """
        for scheme in ('http://', 'https://'):
            if filename.startswith(scheme):
                return True
        return False

    def sanitize_filename(self, filename):
        """ Forwards to HTTPHandler or to FileSystemHandler.
        """
        maybe_url = HTTPHandler.sanitize_filename(self, filename)

        if self.for_http_handler(maybe_url):
            return maybe_url

        return FileSystemHandler.sanitize_filename(self, filename)

    def load_file(self, filename):
        """ Forwards to HTTPHandler or to FileSystemHandler.
        """
        if self.for_http_handler(filename):
            return HTTPHandler.load_file(self, filename)
        return FileSystemHandler.load_file(self, filename)

    def unload_file(self):
        """ Forwards to HTTPHandler or to FileSystemHandler.

        If there's no current session, which happens when the client makes a
        bad request for example, do nothing.
        """
        session = self.get_current_session()

        if not session:
            return

        if self.for_http_handler(session.filename):
            return HTTPHandler.unload_file(self)
        return FileSystemHandler.unload_file(self)
