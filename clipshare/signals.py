from blinker import signal


outgoing_transfer = signal('outgoing_transfer')
incoming_transfer = signal('incoming_transfer')

connection_established = signal('connection_established')
connection_connecting = signal('connection_connecting')
connection_disconnected = signal('connection_disconnected')
