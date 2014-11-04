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
        """ Fowards to HTTPHandler.sanitize_filename() if `filename` is a URL, else to
        FileSystemhandler.sanitize_filename().
        """
        maybe_url = HTTPHandler.sanitize_filename(self, filename)

        if self.for_http_handler(maybe_url):
            return maybe_url

        return FileSystemHandler.sanitize_filename(self, filename)

    def load_file(self, filename):
        """ Fowards to HTTPHandler.load_file() if `filename` is a URL, else to
        FileSystemhandler.load_file().
        """
        if self.for_http_handler(filename):
            return HTTPHandler.load_file(self, filename)
        return FileSystemHandler.load_file(self, filename)
