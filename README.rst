dyntftpd
========

A simple, extendable Python implementation of a TFTP server.

Features:

- Easily customizable (override `dyntftpd.TFTPServer` and `dyntftpd.handlers.*`)
- Can act as a HTTP proxy. The TFTP client can request a HTTP url, the TFTP server downloads and returns it. Beware: making the HTTP request is blocking, so TFTP requests are not handled until we get the HTTP response. If the HTTP server takes long to answer, concurrent TFTP clients will think the server didn't receive their requests, will retry, and the server will eventually overload.
- Code is mostly unit tested and easy to read

Limitations:

- Only handles RRQ requests
- Doesn't drop privileges after creating the listening socket :-(
- No documentation but pydoc


Consider using [hooktftp](https://github.com/tftp-go-team/hooktftp) in production instead of this project. Written in Go, it's **really** more efficient.
