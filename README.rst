dyntftpd
========

A simple, extendable Python implementation of a TFTP server.

Features:

- Easily customizable (override dyntftpd.TFTPServer or dyntftpd.FileSystemHandler)
- Code is mostly unit tested and easy to read

Limitations:

- Only handle RRQ requests
- Don't drop privileges after creating the listening socket
- No documentation but pydoc
