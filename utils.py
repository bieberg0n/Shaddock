import time
from threading import Thread
from config import debug


def log(*args):
    if debug:
        print(*args)


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


def rand_err():
    if debug:
        t = time.time()
        return int(str(t)[-1]) < 2
    else:
        return False


def spawn(target, args=(), wait_exit=False):
    t = Thread(target=target, args=args)
    if not wait_exit:
        t.setDaemon(True)
    t.start()
    return t


def recv_http_header(conn):
    data = conn.recv(2048)
    buf = b''
    while data:
        buf += data
        if buf.endswith(b'\r\n'):
            return buf.decode()
        data = conn.recv(2048)


def host_from_header(header):
    start = header.index('\nHost:') + 7
    header = header[start:]
    end = header.index('\n')
    host = header[:end].strip('\r')

    if ':' in host:
        end = host.index(':')
        host = host[:end]
    return host
