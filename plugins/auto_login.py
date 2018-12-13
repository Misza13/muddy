import os
import re
import json

from muddylib.plugins import MuddyPlugin, IncomingTextHandler


class AutoLoginPlugin(MuddyPlugin):
    seq_position = 0

    @IncomingTextHandler
    def handle(self, line):
        seq_elem = self.configuration['sequence'][self.seq_position]
        
        if seq_elem['type'] == 'expect':
            if line == seq_elem['text']:
                self.advance_seq()
        elif seq_elem['type'] == 'expect_rx':
            if re.search(seq_elem['pattern'], line):
                self.advance_seq()
    
    def advance_seq(self):
        while True:
            self.seq_position += 1
            if self.seq_position == len(self.configuration['sequence']):
                self.seq_position = 0
            
            seq_elem = self.configuration['sequence'][self.seq_position]
            if seq_elem['type'] == 'send':
                self.invoke_method(
                    'Telnet',
                    'send_data',
                    data=self.handle_variables(seq_elem['data']))
            else:
                break
    
    def handle_variables(self, data):
        #TODO: Make this less crude
        if data == '$NAME':
            return self.read_credentials_file()['name']
        elif data == '$PASSWORD':
            return self.read_credentials_file()['password']
        else:
            return data
    
    def read_credentials_file(self):
        p = os.path.expanduser(self.configuration['credentials_file'])
        f = open(p, 'r')
        c = json.loads(f.read())
        return c