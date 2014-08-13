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
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)-15s] %(client_ip)s: %(message)s'
    )
    parser = arguments_parser()
    args = parser.parse_args()
    tftp_server = TFTPServer(args.host, args.port, root=args.root)
    tftp_server.serve_forever()
