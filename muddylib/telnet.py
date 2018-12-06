import zlib

from twisted.internet.protocol import ClientFactory
from twisted.conch.telnet import Telnet

class MudProtocol(Telnet):
    def __init__(self, recv_handler):
        super().__init__()
        self.recv_handler = recv_handler
        self.decompress = zlib.decompressobj()
        self.negotiationMap[b'V'] = lambda data: self.compression_negotiated(data)
        self.compression_enabled = False

    def telnet_WILL(self, option):
        if option == b'V':
            self.do(b'V')

    def compression_negotiated(self, data):
        self.compression_enabled = True

    def dataReceived(self, data):
        if self.compression_enabled:
            data = self.decompress.decompress(data)

        Telnet.dataReceived(self, data)

    def applicationDataReceived(self, data):
        data = data.decode()
        lines = [line.strip('\r') for line in data.split('\n')]
        self.recv_handler(lines)

    def sendData(self, data):
        data += '\n'
        self.transport.write(data.encode('ascii'))

    def connectionLost(self, reason):
        self.recv_handler('Connection lost: ' + str(reason))


class MudClientFactory(ClientFactory):
    def __init__(self, recv_handler, connection_keeper):
        self.recv_handler = recv_handler
        self.connection_keeper = connection_keeper

    def buildProtocol(self, addr):
        proto = MudProtocol(self.recv_handler)
        self.connection_keeper.register(proto)

        return proto


class ConnectionKeeper:
    def __init__(self):
        self.connections = []
    
    def register(self, proto):
        self.connections.append(proto)
    
    #TODO: Use named connections
    def disconnect_all(self):
        for conn in self.connections:
            conn.transport.loseConnection()
    
    #TODO: Use named connections
    def send_all(self, data):
        for conn in self.connections:
            conn.sendData(data)