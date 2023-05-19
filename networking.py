import base64
import json

import rsa
import socket
import threading as th

from typing import Callable, Any


PORT = 13698

BUFFER_SIZE = 2**14
TRANSFER_END = b'\x11packet_transfer_end\x11'


def is_connected(sock: socket.socket | None) -> bool:
    if sock is None:
        return False

    try:
        sock.getsockname()
    except socket.error:
        return False
    return True


class User:
    def __init__(self, s: socket.socket | None = None, **kwargs):
        self.socket: socket.socket | None = s

        self.sock: tuple[str, int] | None = self.socket.getsockname() if self.socket else None
        try:
            self.peer: tuple[str, int] | None = self.socket.getpeername() if self.socket else None
        except socket.error:
            self.peer: tuple[str, int] | None = ("0.0.0.0", PORT) if self.socket else None
        self.username: str = "user_none"

        self.pub_key: rsa.PublicKey | None = None
        self.aes_key: None = None

        for name, val in kwargs.items():
            setattr(self, name, val)

    def __copy__(self):
        return User(**self.__dict__)

    @property
    def addr(self):
        return self.peer.__str__()


class Networking:
    def __init__(self):
        self._socket: socket.socket | None = None
        self._host: bool = False

        self._connected: dict[str, User] = {}
        self._local_ip: str = socket.gethostbyname(socket.gethostname())

        self._aes_key: None = None
        self._pub_key: rsa.PublicKey | None = None
        self._pri_key: rsa.PrivateKey | None = None

        self.rsa_key_size: int = 64
        self.aes_key_size: int = 64

        self.generate_new_rsa_keys(self.rsa_key_size)
        self.generate_new_aes_key(self.aes_key_size)

        self.user: User = User()

        self.ui_print_callback: Callable[[str, str], None] | None = None

    def generate_new_rsa_keys(self, size: int):
        self._pub_key, self._pri_key = rsa.newkeys(size)
        self.rsa_key_size = size

    def generate_new_aes_key(self, size: int):
        # TODO: aes
        self.aes_key_size = size

    def close_connection(self):
        if not is_connected(self._socket):
            return
        if self._host:
            for _, con in self._connected.items():
                con.socket.close()
        else:
            self._socket.close()

    def bind_server(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._local_ip, PORT))
        self._socket.listen(1)

        self._host = True
        self.user = User(self._socket)

        self.ui_print_callback("[NET]", "Connection successful.")

        while True:
            con, _ = self._socket.accept()
            user = User(con)
            self._connected[user.addr] = user

            th.Thread(target=self._request_handler, args=(user,), daemon=True).start()

    def _request_handler(self, user: User):
        self._on_join_server(user)

        buffer: bytes = bytes()
        while True:
            try:
                data = user.socket.recv(BUFFER_SIZE)
            except socket.error:
                self._connected.pop(user.addr)
                user.socket.close()
                self.ui_print_callback("[NET]", "Connection closed.")
                break

            if data[-len(TRANSFER_END):] == TRANSFER_END:
                buffer += data[0:-len(TRANSFER_END)]
                self._decode_packet(buffer)
                self._broadcast_data(buffer + TRANSFER_END, {user.addr})
                buffer = bytes()
            else:
                buffer += data

    def connect_client(self, ip: str):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.connect((ip, PORT))

        server = User(self._socket)
        self._connected[server.peer.__repr__()] = server
        self.user = server.__copy__()

        self.ui_print_callback("[NET]", "Connection successful.")

        buffer: bytes = bytes()
        while True:
            try:
                data = self._socket.recv(BUFFER_SIZE)
            except socket.error:
                self._socket.close()
                self.ui_print_callback("[NET]", "Connection closed.")
                break

            if data[-len(TRANSFER_END):] == TRANSFER_END:
                buffer += data[0:-len(TRANSFER_END)]
                self._decode_packet(buffer)
                buffer = bytes()
            else:
                buffer += data

    def _decode_packet(self, pack: bytes):
        # print(pack)

        dec = json.loads(pack.decode("ascii"))
        if "data" in dec:
            dec["data"] = base64.b64decode(dec["data"])

        # print(dec)
        # print(self._connected)

        if dec["addr"] not in self._connected:
            self._connected[dec["addr"]] = User()

        match dec["type"]:
            case "join":
                pass
            case "message":
                self.ui_print_callback(self._connected[dec["addr"]].username, dec["data"].decode("utf-8"))
            case "request":
                if "username" in dec:
                    self._connected[dec["addr"]].username = dec["username"]
                if "rsa_key" in dec:
                    self._connected[dec["addr"]].pub_key = rsa.PublicKey.load_pkcs1(dec["rsa_key"])
                if "aes_key" in dec:
                    pass
            case _:
                pass

    def _generate_payload(self, type_: str, data: bytes | str | None = None, **kwargs) -> bytes:
        packet = {
            "type": type_,
            "addr": self._socket.getsockname().__repr__()}

        if data:
            if isinstance(data, bytes):
                d = base64.b64encode(data).decode('ascii')
            else:
                d = data
            packet.update({"data": d})

        packet.update(kwargs)
        encrypted = json.dumps(packet).encode("ascii")
        return encrypted + TRANSFER_END

    def _broadcast_data(self, data: bytes, exceptions: set | None = None):
        if exceptions is None:
            exceptions = {}
        if self._host:
            for _, con in self._connected.items():
                if con.addr not in exceptions:
                    con.socket.send(data)
        else:
            self._socket.send(data)

    def _on_join_server(self, user: User):
        pass

    def change_username(self, new_username: str):
        self.user.username = new_username
        self._broadcast_data(
            self._generate_payload(
                type_="request",
                username=new_username))

    def send_message(self, message: str):
        self._broadcast_data(
            self._generate_payload(
                type_="message",
                data=message.encode("utf-8")))

    @property
    def get_local_ip(self):
        return self._local_ip

    @property
    def connections(self):
        return self._connected

    @property
    def get_pub_key(self):
        return self._pub_key

    @property
    def is_connected(self):
        return is_connected(self._socket)
