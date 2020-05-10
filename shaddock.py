import socket
import ssl
from utils import (
spawn,
log,
recv_http_header,
host_from_header,
)
import config


class Shaddock:
    def __init__(self, port, cfgs):
        self.port = port
        self.cfgs = cfgs
        self.ssl_ctx = {}
        self.default_ssl_ctx = None

        for name, cfg in cfgs.items():
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(*cfg['cert'])
            self.ssl_ctx[name] = ctx
            if self.default_ssl_ctx is None:
                self.default_ssl_ctx = ctx

    def sni_callback(self, conn, name, _):
        ctx = self.ssl_ctx.get(name)
        if not ctx:
            ctx = self.default_ssl_ctx
        conn.context = ctx

    def relay(self, left, right):
        data = left.recv(1024 * 2)
        while data:
            right.sendall(data)
            data = left.recv(1024 * 2)

        right.shutdown(socket.SHUT_RDWR)

    def handle(self, conn, addr):
        header = recv_http_header(conn)
        log(header)

        host = host_from_header(header)
        if self.cfgs.get(host) is None:
            up_ip, up_port = '127.0.0.1', 2015

        else:
            upstream = self.cfgs[host]['upstream']
            up_ip, up_port_str = upstream.split(':')
            up_port = int(up_port_str)

        right = socket.socket()
        right.connect((up_ip, up_port))
        right.sendall(header.encode())

        t = spawn(self.relay, (conn, right))
        self.relay(right, conn)
        t.join()

        conn.close()
        right.close()

    def run(self):
        ctx = list(self.ssl_ctx.values())[0]
        ctx.sni_callback = self.sni_callback

        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', self.port))
        s.listen(5)

        while True:
            conn, addr = s.accept()
            conn = ctx.wrap_socket(conn, server_side=True)
            spawn(self.handle, (conn, addr))


def main():
    for p in config.servers:
        s = Shaddock(p, config.servers[p])
        spawn(s.run, wait_exit=True)


if __name__ == '__main__':
    main()
