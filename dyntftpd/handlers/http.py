import base64
import contextlib
import datetime
import errno
import logging
import os
import re
import time
import urllib

import requests

from . import TFTPUDPHandler, TFTPSession


class Session(TFTPSession):

    def __init__(self, tftp_handler, filename):
        """ Cient needs to urlencode the filename he wants to request.
        """
        url = urllib.unquote(filename)
        super(Session, self).__init__(tftp_handler, url)

    def load_file(self):
        """ Downloads `self.filename` to the cache directory, and return the cached
        file.
        """
        self.tftp_handler._log(logging.INFO, 'Downloading %s' % self.filename)

        # Create cache directory if doesn't already exist
        cache_dir = self.get_config(
            'cache_dir', '/var/cache/dyntftpd/handlers/http'
        )
        try:
            os.makedirs(cache_dir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

        # Create local file where remote file is stored
        safe_name = '%s_%s_%s_%s' % (
            base64.b64encode(self.filename),
            self.tftp_handler.client_address[0],
            self.tftp_handler.client_address[1],
            datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        )
        local_filename = os.path.join(cache_dir, safe_name)
        local_file = open(local_filename, 'w+')

        # Download `self.filename` to `local_file`
        try:
            for block in self._download(self.filename):
                local_file.write(block)

        # Clean if there was an error
        except IOError as exc:
            # Local file partially written, display a message for investigation
            self.tftp_handler._log(
                logging.ERROR,
                'Error while downloading %s. Downloaded content has been '
                'stored to %s' % (self.filename, local_filename), exc_info=True
            )

            local_file.close()
            raise

        self.tftp_handler._log(
            logging.INFO,
            '%s successfully downloaded to %s' % (self.filename,
                                                  local_filename)
        )

        return local_file

    def get_config(self, name, default):
        """ Fetchs `name` in handler arguments, or return `default`.
        """
        sentinel = object()
        config = self.tftp_handler.server.handler_args.get(
            'http', {}
        ).get(name, sentinel)
        if config is sentinel:
            return default
        return config

    def _download(self, filename):
        """ Downloads `filename` and yield its content block by block.

        To limit DoS, a timeout and a filesize limit are set, redirections are
        denied, and it is possible to set a whitelist of sites where downloads
        are authorized.
        """
        timeout = self.get_config('timeout', 3)
        maxsize = self.get_config('maxsize', 1000000 * 50)  # 50M
        requests_kwargs = self.get_config('requests_kwargs', {
            'allow_redirects': False
        })
        whitelist = self.get_config('whitelist', [r'.*'])

        for domain in whitelist:
            if re.match(domain, filename):
                break
        else:
            raise IOError('Forbidden domain (not whitelisted)')

        start_time = time.time()

        with contextlib.closing(
            requests.get(filename, stream=True, timeout=timeout,
                         **requests_kwargs)
        ) as res:

            # can only be true if redirection and allow_redirects is False
            if 300 <= res.status_code <= 400:
                raise IOError('Redirections are forbidden. Download aborted.')

            if not res.ok:
                raise IOError('GET %s returned HTTP/%s' % (filename,
                                                           res.status_code))

            size = 0

            for data in res.iter_content(chunk_size=8192):
                yield data

                size += len(data)

                if time.time() > start_time + timeout:
                    raise IOError(
                        '%s took more than %s seconds to download. Abort.' % (
                            filename, timeout
                        ))

                if size > maxsize:
                    raise IOError('Failed to download %s. '
                                  'More than %s bytes.' % (filename, size))

    def unload_file(self):
        self.handle.close()


class HTTPHandler(TFTPUDPHandler):
    """ Serve HTTP files by TFTP for clients that don't have a HTTP client
    (a bootloader like u-boot, for example).
    """

    session_cls = Session
