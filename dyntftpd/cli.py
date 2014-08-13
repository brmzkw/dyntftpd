import argparse
import logging

from .server import TFTPServer


def arguments_parser():
    parser = argparse.ArgumentParser(
        description='Extendable TFTP server, implemented in Python'
    )
    parser.add_argument('--host', '-H', default='')
    parser.add_argument('--port', '-p', default=69, type=int)
    parser.add_argument(
        '--root', '-r', default='/var/lib/tftpboot/', help='TFTP root folder'
    )
    return parser


def main():
    parser = arguments_parser()
    parser.add_argument(
        '-v', dest='verbose', action='count', default=0, help='Verbose mode'
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)-15s] %(client_ip)s: %(message)s'
    )

    tftp_server = TFTPServer(args.host, args.port, root=args.root)
    tftp_server.serve_forever()
