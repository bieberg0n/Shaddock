import os
import time
import queue
import signal
import socket
import ssl
from httpheader import HttpHeader
import utils
from utils import (
spawn,
log,
plog,
)
import config


class Shaddock:
    def __init__(self, port, cfgs, reload_sign):
        self.port: int = port
        self.cfgs = cfgs
        self.reload_sign: queue.Queue = reload_sign

        self.domain_match_dict = self.make_domain_match_dict()
        plog(self.domain_match_dict)

        self.ssl_ctx = {}
        self.default_ssl_ctx = None

    def load_ssl_ctxs(self):
        log('load ssl ctxs')
        if not self.ssl_enabled():
            return

        self.ssl_ctx = {name: self.load_ssl_ctx_from_cfg(cfg) for name, cfg in self.cfgs.items()}
        self.default_ssl_ctx = self.ssl_ctx.values()[0]
        self.default_ssl_ctx.sni_callback = self.sni_callback

    def load_ssl_ctx_from_cfg(self, cfg):
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(*cfg['cert'])
        return ctx

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

            if not self.reload_sign.empty():
                self.reload_sign.get()
                self.load_ssl_ctxs()

            if self.ssl_enabled():
                spawn(self.ssl_wrap_handle, (conn, addr))
            else:
                spawn(self.handle, (conn, addr))


class Supervisor:
    def __init__(self):
        self.sign_queues: [queue.Queue] = []
        signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)

    def handle_SIGUSR1(self, _signum, _frame):
        log('receive reload sign!')
        for q in self.sign_queues:
            q.put(True)

    def run(self):
        pid = os.getpid()
        log('my PID:', pid)
        with open('pid.txt', 'w') as f:
            f.write(str(pid))

        for p in config.servers:
            q = queue.Queue()
            self.sign_queues.append(q)
            s = Shaddock(p, config.servers[p], q)
            log('listen on:', p)
            spawn(s.run, daemon=False)


def main():
    supervisor = Supervisor()
    supervisor.run()


if __name__ == '__main__':
    main()
