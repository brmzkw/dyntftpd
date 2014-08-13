import argparse

from .server import TFTPServer


def main():
    parser = argparse.ArgumentParser(
        description='Extendable TFTP server, implemented in Python'
    )
    parser.add_argument('--host', '-H', default='')
    parser.add_argument('--port', '-p', default=69, type=int)
    parser.add_argument('--root', '-r', default='/var/lib/tftpboot/')
    args = parser.parse_args()

    tftp_server = TFTPServer(args.host, args.port, root=args.root)
    tftp_server.serve_forever()
