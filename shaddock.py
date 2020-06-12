import time
import socket
import ssl
import utils
from utils import (
spawn,
log,
HttpHeader,
)
import config


class Shaddock:
    def __init__(self, port, cfgs):
        self.port = port
        self.cfgs = cfgs
        self.domain_match_dict = self.make_domain_match_dict()
        utils.plog(self.domain_match_dict)

        if not self.ssl_enabled():
            return

        self.ssl_ctx = {}
        self.default_ssl_ctx = None

        for name, cfg in cfgs.items():
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(*cfg['cert'])
            self.ssl_ctx[name] = ctx

            if self.default_ssl_ctx is None:
                ctx.sni_callback = self.sni_callback
                self.default_ssl_ctx = ctx

    def ssl_enabled(self):
        return any([cfg.get('cert') for cfg in self.cfgs.values()])

    def sni_callback(self, conn, name, _):
        ctx = self.ssl_ctx.get(name)
        if ctx is None:
            for n, c in self.ssl_ctx.items():
                if n.startswith('*') and name.endswith(n[1:]):
                    ctx = c
                    break
            else:
                ctx = self.default_ssl_ctx
        conn.context = ctx

    def make_domain_match_dict(self):
        d = dict()
        for name, cfg in self.cfgs.items():
            ns = name.split('.')
            utils.list_to_dict(ns, d, cfg)

        return d

    def domain_match(self, name):
        d = self.domain_match_dict
        o = d
        for n in reversed(name.split('.')):
            new_o = o.get(n)
            if new_o is None:
                return o.get('*')
            else:
                o = new_o
        else:
            return new_o

    def relay(self, left, right):
        data = left.recv(1024 * 2)
        while data:
            # log(data)
            right.sendall(data)
            data = left.recv(1024 * 2)

        right.shutdown(socket.SHUT_RDWR)

    def handle(self, conn, addr):
        header = HttpHeader.load_from_conn(conn)
        host, _ = utils.host_to_addr(header.host)
        log(time.ctime(), header.method, host + header.path)

        cfg = self.domain_match(host)

        if cfg.get('x-forward-for'):
            header.args['X-Forwarded-For'] = addr[0]

        if cfg.get('-'):
            for arg in cfg['-']:
                utils.del_key(header.args, arg)

        up_ip, up_port = utils.host_to_addr(cfg['upstream'])

        right = socket.socket()
        right.connect((up_ip, up_port))
        right.sendall(header.encode())

        t = spawn(self.relay, (conn, right))
        self.relay(right, conn)
        t.join()

        conn.close()
        right.close()

    def ssl_wrap_handle(self, conn, addr):
        ctx = self.default_ssl_ctx
        conn = ctx.wrap_socket(conn, server_side=True)
        self.handle(conn, addr)

    def run(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', self.port))
        s.listen(5)

        while True:
            conn, addr = s.accept()
            if self.ssl_enabled():
                spawn(self.ssl_wrap_handle, (conn, addr))
            else:
                spawn(self.handle, (conn, addr))


def main():
    for p in config.servers:
        s = Shaddock(p, config.servers[p])
        log(p)
        spawn(s.run, daemon=False)


if __name__ == '__main__':
    main()
