Changelog
=========

0.4.0 (2015-04-16)
------------------

* In HTTP handler, the cache filename contains client's source port and human
  readable datetime, making debugging easier.
* We no longer create a thread for each request.
* API break: move load_file and unload_file from TFTP handlers to Session.
* Use CleverHandler instead of FileSystemHandler by default.
* Free resources if client disconnect before completing a transfert.

0.3.0 (2015-02-05)
------------------

* Add unload_file callback in TFTPUDPHandler, called when the transfer of a
  file is over and successful.
* Remove cache files for successful transfers in HTTPHandler.

0.2.1 (2014-11-06)
------------------

* Create HTTPHandler.
* Create CleverHandler to dispatch to HTTPHandler or FileSystemHandler
  depending on the requested file.

0.2.0 (2014-10-13)
------------------

* Use ThreadingMixin to serve multiple requests at the same time.
* Accept option blksize.

0.1.1 (2014-09-29)
------------------

* Accept, and ignore extra request options.

0.1.0 (2014-09-08)
------------------

* Initial release.
* Only accept TFTP read requests.
