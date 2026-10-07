from PyQt5.QtCore import pyqtSignal, pyqtSlot, QByteArray
from PyQt5.QtNetwork import QTcpSocket, QAbstractSocket
from PyQt5.QtCore import QDataStream, QObject, QIODevice


class HNNKTcpSocketClient(QObject):
    server_connected = pyqtSignal()
    server_disconnected = pyqtSignal()
    recv_from_server = pyqtSignal(QByteArray)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self.on_server_connected)
        self.socket.disconnected.connect(self.on_server_disconnected)
        self.socket.readyRead.connect(self.on_recv_from_server)
        self.recv_buffer = QByteArray()

    def connect_server(self, ip, port):
        self.recv_buffer.clear()
        self.socket.connectToHost(ip, port)

    def close_server(self):
        self.recv_buffer.clear()
        self.socket.disconnectFromHost()

    def send_to_server(self, data):
        if self.socket.state() != QAbstractSocket.ConnectedState:
            return

        payload = QByteArray(data)

        packet = QByteArray()
        stream = QDataStream(packet, QIODevice.WriteOnly)
        stream.setByteOrder(QDataStream.BigEndian)

        stream.writeUInt32(payload.size())
        packet.append(payload)

        self.socket.write(packet)

    @pyqtSlot()
    def on_server_connected(self):
        self.server_connected.emit()

    @pyqtSlot()
    def on_server_disconnected(self):
        self.server_disconnected.emit()

    @pyqtSlot()
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
