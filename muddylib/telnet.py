import zlib

from pubsub import pub

from twisted.internet.protocol import ClientFactory
from twisted.conch.telnet import Telnet


class MudProtocol(Telnet):
    def __init__(self):
        super().__init__()
        self.decompress = zlib.decompressobj()
        self.negotiationMap[b'V'] = lambda data: self.compression_negotiated(data)
        self.negotiationMap[b'\xC9'] = lambda data: self.gmcp(data)
        self.compression_enabled = False

    def telnet_WILL(self, option):
        if option == b'V':
            self.do(b'V')
        elif option == b'\xC9':
            self.do(b'\xC9')

    def compression_negotiated(self, data):
        self.compression_enabled = True

    def gmcp(self, data):
        with open('muddy-gmcp.log', 'a') as l:
            l.write(repr(b''.join(data)) + '\n')
            l.flush()

    def dataReceived(self, data):
        if self.compression_enabled:
            data = self.decompress.decompress(data)

        Telnet.dataReceived(self, data)

    def applicationDataReceived(self, data):
        data = data.decode()
        lines = [line.strip('\r') for line in data.split('\n')]
        pub.sendMessage('Core.telnet_received', text=lines)

    def sendData(self, data):
        data += '\n'
        self.transport.write(data.encode('ascii'))

    def connectionLost(self, reason):
        pub.sendMessage('Core.telnet_received', text=['Connection lost: ' + str(reason)])


class MudClientFactory(ClientFactory):
    def __init__(self, conn_built_handler):
        self.conn_built_handler = conn_built_handler

    def buildProtocol(self, addr):
        proto = MudProtocol()
        self.conn_built_handler(proto)

        return proto


class ConnectionKeeper:
    def __init__(self):
        self.connection = None
        pub.subscribe(self.send_data, 'Telnet.send_data')
    
    def register(self, proto):
        self.connection = proto
    
    def disconnect(self):
        if self.connection:
            self.connection.transport.loseConnection()
    
    def send_data(self, data):
        if self.connection:
            self.connection.sendData(data)