from PyQt5.QtCore import pyqtSignal, QByteArray
from PyQt5.QtNetwork import QLocalSocket
from PyQt5.QtCore import QDataStream, QObject, QIODevice


class HNNKLocalSocketClient(QObject):
    server_connected = pyqtSignal()
    server_disconnected = pyqtSignal()
    recv_from_server = pyqtSignal(QByteArray)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.socket = QLocalSocket(self)
        self.socket.connected.connect(self.on_server_connected)
        self.socket.disconnected.connect(self.on_server_disconnected)
        self.socket.readyRead.connect(self.on_recv_from_server)
        self.recv_buffer = QByteArray()

    def connect_server(self, server_name):
        self.recv_buffer.clear()
        self.socket.connectToServer(server_name)

    def close_server(self):
        self.recv_buffer.clear()
        self.socket.disconnectFromServer()

    def send_to_server(self, data):
        if self.socket.state() != QLocalSocket.ConnectedState:
            return

        payload = QByteArray(data)

        packet = QByteArray()
        stream = QDataStream(packet, QIODevice.WriteOnly)
        stream.setByteOrder(QDataStream.BigEndian)

        stream.writeUInt32(payload.size())
        packet.append(payload)

        self.socket.write(packet)

    def on_server_connected(self):
        self.server_connected.emit()

    def on_server_disconnected(self):
        self.server_disconnected.emit()

    def on_recv_from_server(self):
        self.recv_buffer.append(self.socket.readAll())

        while True:
            if self.recv_buffer.size() < 4:
                return

            stream = QDataStream(self.recv_buffer)
            stream.setByteOrder(QDataStream.BigEndian)
            payload_len = stream.readUInt32()

            total_len = 4 + payload_len
            if self.recv_buffer.size() < total_len:
                return

            payload = self.recv_buffer.mid(4, payload_len)
            self.recv_buffer.remove(0, total_len)

            self.recv_from_server.emit(payload)
