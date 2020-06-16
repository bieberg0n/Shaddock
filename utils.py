import time
from pprint import pprint
from threading import Thread
from config import debug


def log(*args):
    if debug:
        print(*args)


def plog(*args):
    if debug:
        pprint(*args)


def info(*args):
    print(*args)


def recv(conn):
    buf = b''
    while True:
        data = conn.recv(1)
        if data == b'\n':
            break
        elif data == b'':
            return None
        else:
            buf += data

    length = int(buf.decode())

    b = b''
    while len(b) < length:
        data = conn.recv(length - len(b))
        b += data

    return b


def recv_by_len(conn, length):
    buf = b''
    while len(buf) < length:
        data = conn.recv(length - len(buf))
        if data == b'':
            return buf
        else:
            buf += data

    return buf


def rand_err():
    if debug:
        t = time.time()
        return int(str(t)[-1]) < 2
    else:
        return False


def spawn(target, args=(), daemon=True):
    t = Thread(target=target, args=args)
    t.setDaemon(daemon)
    t.start()
    return t


def del_key(dic, key):
    if dic.get(key):
        del dic[key]


class HttpHeader:
    def __init__(self):
        self.conn = None
        self.method = ''
        self.path = ''
        self.http_type = ''
        self.status_code = ''
        self.args = {}
        self.host = ''
        self.body = ''

    def recv_http_header_raw(self, conn):
        data = conn.recv(2048).decode()
        buf = ''
        while data:
            buf += data
            if '\r\n\r\n' in buf:
                h, b = buf.split('\r\n\r\n')
                self.body = b
                return h
            assert len(buf) < 1024 * 1024
            data = conn.recv(2048).decode()

    def load(self, header_str):
        headers_lines = header_str.split('\r\n')
        headers_head = headers_lines[0].split(' ')
        self.method, self.path, self.http_type = headers_head
        for line in headers_lines[1:]:
            if line:
                key, value = line.split(': ')[:2]
                self.args[key] = value

        body_len = self.args.get('Content-Length')
        if body_len:
            l = int(body_len) - len(self.body)
            self.body += recv_by_len(self.conn, l).decode()

    @staticmethod
    def load_from_conn(conn):
        header = HttpHeader()
        header.conn = conn

        data = header.recv_http_header_raw(conn)
        header.load(data)

        host = header.args.get('Host')
        if host:
            header.host = host
        return header

    def encode(self):
        top = '{} {} {}\r\n'.format(self.method, self.path, self.http_type)
        body = '\r\n'.join(['{}: {}'.format(k, v) for k, v in self.args.items()])
        raw = top + body + '\r\n\r\n' + self.body
        return raw.encode()


#  [a, b, c] => {'a': {'b': 'c'}}
def list_to_dict(ls, d, value):
    # ls = list(reversed(ls))
    return _list_to_dict(ls, d, value, d)


# [c, b, a], v => {'a': {'b': 'c': v}}
def _list_to_dict(ls, o, value, d):
    if len(ls) == 0:
        return d

    e = ls.pop()
    if len(ls) == 0:
        o[e] = value
        return d

    elif o.get(e) is None:
        new_o = dict()
        o[e] = new_o
    else:
        new_o = o.get(e)
    return _list_to_dict(ls, new_o, value, d)


def host_to_addr(host, default_port=80):
    if ':' in host:
        h, port_str = host.split(':')
        port = int(port_str)
    else:
        h, port = host, default_port

    return h, port
