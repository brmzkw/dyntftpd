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

    def sanitize_filename(self, filename):
        """ Cient needs to urlencode the filename he wants to request.
        """
        return urllib.unquote(filename)

    def load_file(self, filename, local_dir='/tmp/tftpcache'):
        """ Downloads `filename` to `local_dir`, and returns the local file.
        """
        self._log(logging.INFO, 'Downloading %s' % filename)

        # Create local file where remote file is stored
        safe_name = base64.b64encode(filename)
        local_filename = os.path.join(local_dir, safe_name)
        local_file = open(local_filename, 'w+')

        # Create local_dir if doesn't already exist
        try:
            os.makedirs(local_dir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

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
