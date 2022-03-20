import utils


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
            length = int(body_len) - len(self.body.encode())
            self.body += utils.recv_by_len(self.conn, length).decode()

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
