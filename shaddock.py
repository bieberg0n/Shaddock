import socket
from utils import (
spawn,
log,
)


class Shaddock:
    def __init__(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 2222))
        s.listen(5)
        self.s = s

    def relay(self, left, right):
        data = left.recv(1024 * 4)
        while data:
            right.sendall(data)
        right.shutdown(socket.SHUT_RDWR)

    def handle(self, conn):
        right = socket.socket()
        right.connect(('127.0.0.1', 8091))
        t = spawn(self.relay, (conn, right))
        self.relay(right, conn)
        t.join()
        conn.close()
        right.close()

    def run(self):
        while True:
            conn, addr = self.s.accept()
            spawn(self.handle, (conn,))


def main():
    serv = Shaddock()
    serv.run()


if __name__ == '__main__':
    main()
