import socket
from dataclasses import dataclass
from httpheader import HttpHeader

@dataclass
class Context:
    left_conn: socket.socket
    src_addr: (str, int)
    cfg: map = None
    header: HttpHeader = None
    right_conn: socket.socket = None
