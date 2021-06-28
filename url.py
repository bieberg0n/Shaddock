import utils

class Protocol:
    http = 'http'
    https = 'https'
    unix = 'unix'


class URL:
    def __init__(self, url: str):
        self.protocol = ''
        self.host = ''
        self.port = 0

        if url.startswith('http://'):
            self.protocol = Protocol.http
        elif url.startswith('https://'):
            self.protocol = Protocol.https
        elif url.startswith('unix://'):
            self.protocol = Protocol.unix
        else:
            self.protocol = Protocol.http

        url = utils.removeprefix(url, self.protocol + '://')

        if ':' in url:
            self.host, port_str = url.split(':')
            self.port = int(port_str)
        else:
            self.host, self.port = url, 80
