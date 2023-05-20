import json
import base64
import socket
import threading as th

from typing import Callable


PORT = 13698

BUFFER_SIZE = 2**14
TRANSFER_DELIMITER = b'\x2c\xae\x47\x6b\x39\xaetransfer_end\x28\x41\x2c\xa3\xae\x2c'

RSA_KEY_SIZE = 1024 * 3
AES_KEY_SIZE = 256


class User:
    def __init__(self, **kwargs):
        self.socket: socket.socket | None = None
        self.sock: tuple[str, int] | None = None
        self.peer: tuple[str, int] | None = None

        self.nick: str = "user"

        self.rsa_pub_key: None = None
        self.rsa_pri_key: None = None
        self.aes_key: None = None

        self.rsa_size: int = 64
        self.aes_size: int = 64

        for name, val in kwargs.items():
            setattr(self, name, val)

    def __copy__(self):
        return type(self)(**self.__dict__)

    def gen_new_rsa(self, size: int | None = None):
        if size is None:
            self.rsa_size = RSA_KEY_SIZE
        else:
            self.rsa_size = size

    def gen_new_aes(self, size: int | None = None):
        if size is None:
            self.aes_size = AES_KEY_SIZE
        else:
            self.aes_size = size

    def close(self):
        Clients.close(self)

    def assign_socket(self, sock: socket.socket, host: bool = False):
        self.socket = sock
        self.sock = self.socket.getsockname()
        self.peer = self.socket.getpeername() if not host else self.sock
        self.nick += self.addr

    @property
    def connected(self) -> bool:
        if self.socket is None:
            return False
        try:
            self.socket.getsockname()
        except socket.error:
            return False
        return True

    @property
    def addr(self) -> str:
        return "_".join([str(x) for x in self.peer])

    @property
    def sock_addr(self) -> str:
        return "_".join([str(x) for x in self.sock])

    @property
    def ip(self) -> str:
        return self.peer[1]

    @property
    def sock_ip(self) -> str:
        return self.sock[1]


class Clients:
    clients: list[User] = []

    _name_to_client: dict[str, int] = {}
    _addr_to_client: dict[str, int] = {}

    @staticmethod
    def by_name(name: str) -> User | None:
        if name in Clients._name_to_client:
            return Clients.clients[Clients._name_to_client[name]]

    @staticmethod
    def by_addr(addr: str) -> User | None:
        if addr in Clients._addr_to_client:
            return Clients.clients[Clients._addr_to_client[addr]]

    @staticmethod
    def add(client: User):
        if client.nick in Clients._name_to_client:
            client.nick += client.addr
        Clients._name_to_client[client.nick] = len(Clients.clients)
        Clients._addr_to_client[client.addr] = len(Clients.clients)
        Clients.clients.append(client)

    @staticmethod
    def pop(client: User | str):
        if isinstance(client, User):
            Clients.clients.pop(Clients._addr_to_client[client.addr])
            Clients._addr_to_client.pop(client.addr)
            Clients._name_to_client.pop(client.nick)
        elif isinstance(client, str):
            index = Clients._name_to_client.get(client)
            if index is None:
                raise KeyError
            client = Clients.clients[index]
            Clients._addr_to_client.pop(client.addr)
            Clients._name_to_client.pop(client.nick)
            Clients.clients.pop(index)
        else:
            raise TypeError

    @staticmethod
    def close(client: User | str):
        if isinstance(client, User):
            client.socket.close()
            Clients.pop(client)
        elif isinstance(client, str):
            c = Clients.by_name(client)
            if c is None:
                raise KeyError
            Clients.pop(c)


class Networking:
    def __init__(self):
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.user: User = User()
        self.hosting: bool = False
        self._ip = socket.gethostbyname(socket.gethostname())

        self.ui_print: Callable[[str, str], None] | None = None

    def assign_ui_callback(self, func: Callable[[str, str], None]):
        self.ui_print = func

    def close(self):
        assert self.user.connected
        if self.hosting:
            for client in Clients.clients:
                client.close()
        else:
            self.user.close()

    def connect_client(self, ip: str):
        self.socket.connect((ip, PORT))

        self.user.assign_socket(self.socket)
        Clients.add(self.user.__copy__())
        self.user.nick = "user" + self.user.sock_addr

        self.ui_print("[NET]", f"Connection successful! You are connected to {self.user.addr}")

        buffer: bytes = bytes()
        while True:
            try:
                data = self.socket.recv(BUFFER_SIZE)
            except socket.error:
                self.ui_print("NET", f"Connection closed for {Clients.by_addr(self.user.addr).nick} "
                                     f"| {Clients.by_addr(self.user.addr).addr}")
                self.socket.close()
                break

            if data[-len(TRANSFER_DELIMITER):] == TRANSFER_DELIMITER:
                buffer += data[0:-len(TRANSFER_DELIMITER)]
                # self._decode_packet(buffer)
                buffer = bytes()
            else:
                buffer += data

    def bind_server(self):
        self.socket.bind((self._ip, PORT))
        self.socket.listen(1)

        self.hosting = True
        self.user.assign_socket(self.socket, self.hosting)

        self.ui_print("[NET]", "Connection successful! You are the host")

        while True:
            sock, _ = self.socket.accept()
            client = User()
            client.assign_socket(sock)
            Clients.add(client)

            th.Thread(target=self._request_handler, args=(client,), daemon=True).start()

    def _request_handler(self, client: User):
        buffer: bytes = bytes()
        while True:
            try:
                data = client.socket.recv(BUFFER_SIZE)
            except socket.error:
                self.ui_print("NET", f"Connection closed for {client.nick} | {client.addr}")
                Clients.pop(client)
                break

            if data[-len(TRANSFER_DELIMITER):] == TRANSFER_DELIMITER:
                buffer += data[0:-len(TRANSFER_DELIMITER)]
                # self._decode_packet(buffer)
                # self._broadcast_data(buffer + TRANSFER_DELIMITER, {client})
                buffer = bytes()
            else:
                buffer += data

    def send_message(self, text: str):
        pass

    def change_username(self, username: str):
        pass

    @property
    def local_ip(self):
        return self._ip


def test():
    net = Networking()


if __name__ == '__main__':
    test()
