import getpass
from mcserver import MCServer

print 'Ctrl-C to exit'

# get the host
host = raw_input('Host: ')
if not host:
	host = "localhost"

# get the port for Rcon
rconPort = raw_input('Rcon Port (25575): ')
if not rconPort:
	rconPort = 25575
else:
	rconPort = int(rconPort)

# get the port for Query
queryPort = raw_input('Query Port (25575): ')
if not queryPort:
	queryPort = 25575
else:
	queryPort = int(queryPort)

# get the Rcon password
pwd  = getpass.getpass('Password: ')

# connect!
print "Connecting..."
server = MCServer(host=host, queryPort=queryPort, rconPort=rconPort, password=pwd)
print "Logged in successfully"

try:
    while True:
        line = raw_input('Rcon: ')
        print server.cmd(line)
except KeyboardInterrupt, e:
	server.close()