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
