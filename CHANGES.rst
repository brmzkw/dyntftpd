Changelog
=========

0.3.1 (unreleased)
------------------

* No entry... yet.

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
