dyntftpd
========

A simple, extendable Python implementation of a TFTP server.

Features:

- Easily customizable (override dyntftpd.TFTPServer and dyntftpd.handlers.*)
- Can act as a HTTP proxy. The TFTP client can request a HTTP url, the TFTP
  server downloads and returns it.
- Code is mostly unit tested and easy to read

Limitations:

- Only handle RRQ requests
- Don't drop privileges after creating the listening socket :-(
- No documentation but pydoc
