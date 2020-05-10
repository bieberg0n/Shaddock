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


def spawn(target, args=()):
    t = Thread(target=target, args=args)
    t.setDaemon(True)
    t.start()
    return t
