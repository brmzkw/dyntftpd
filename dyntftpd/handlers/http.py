import base64
import contextlib
import errno
import logging
import os
import urllib

import requests

from . import TFTPUDPHandler


class HTTPHandler(TFTPUDPHandler):
    """ Serve HTTP files by TFTP for clients that don't have a HTTP client
    (like a bootloader like u-boot, for example).
    """

    def get_config(self, name, default):
        """ Fetchs `name` in handler arguments, or return `default`.
        """
        sentinel = object()
        config = self.server.handler_args.get('http', {}).get(name, sentinel)
        if config is sentinel:
            return default
        return config

    def sanitize_filename(self, filename):
        """ Cient needs to urlencode the filename he wants to request.
        """
        return urllib.unquote(filename)

    def load_file(self, filename):
        """ Downloads `filename` to the cache directory, and return the cached
        file.
        """
        self._log(logging.INFO, 'Downloading %s' % filename)

        # Create cache directory if doesn't already exist
        cache_dir = self.get_config('cache_dir', '/tmp/tftpcache')
        try:
            os.makedirs(cache_dir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

        # Create local file where remote file is stored
        safe_name = base64.b64encode(filename)
        local_filename = os.path.join(cache_dir, safe_name)
        local_file = open(local_filename, 'w+')

        # Download `filename` to `local_file`
        try:
            with contextlib.closing(
                requests.get(filename, stream=True)
            ) as res:

                if not res.ok:
                    raise IOError('GET %s returned HTTP/%s' % (
                        filename, res.status_code
                    ))

                for block in res.iter_content(4096):
                    local_file.write(block)

        # Clean if there was an error
        except IOError as exc:
            # Local file is empty, remove it
            if not local_file.tell():
                os.unlink(local_filename)

            # Local file partially written, display a message for investigation
            else:
                self._log(
                    logging.ERROR,
                    'Error while downloading %s. Downloaded content has been '
                    'stored to %s' % (filename, local_filename), exc_info=True
                )

            local_file.close()
            raise

        self._log(logging.INFO, '%s successfully downloaded to %s' % (
            filename, local_filename
        ))

        return local_file
