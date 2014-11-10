#!/usr/bin/python
# -*- coding: utf-8 -*-
import socket, select, struct, re

def cleanup(text): # because the results try to create colours and therefore have horrible characters in them
    return(text.replace("§c","").replace("§a","").replace("§6","").replace("§4","").replace("\xc2\xa7d","").rstrip())

class MCServer:
    id = 0
    retries = 0
    max_retries = 3
    timeout = 10
    def __init__(self, host=None, rconPort=None, password=None, queryPort=None, **kargs):
        self.cmds = dir(self)[3:]
        self.password = password
        if 'max_retries' in kargs:
            self.max_retries = kargs['max_retries']
        if 'timeout' in kargs:
            self.timeout = kargs['timeout']

        self.q_addr = (host, queryPort)
        self.q_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.q_s.settimeout(self.timeout)
        self.handshake()

        self.r_addr = (host, rconPort)
        self.r_password = password
        self.r_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.r_s.connect(self.r_addr)
        self.send_real(3, password)


                            # begin query
    def write_packet(self, type, payload):
        o = '\xFE\xFD' + struct.pack('>B', type) + struct.pack('>l', self.id) + payload
        self.q_s.sendto(o, self.q_addr)
    
    def read_packet(self):
        buff = self.q_s.recvfrom(2048)[0]
        type = struct.unpack('>B', buff[0])[0]
        id   = struct.unpack('>l', buff[1:5])[0]
        return type, id, buff[5:]
    
    def handshake(self):
        self.id += 1
        self.write_packet(9, '')
        try:
            type, id, buff = self.read_packet()
        except:
            self.retries += 1
            if self.retries == self.max_retries:
                raise Exception('Retry limit reached - server down?')
            return self.handshake()
        
        self.retries = 0
        self.challenge = struct.pack('>l', int(buff[:-1]))
    
    def basic_stats(self):
        self.write_packet(0, self.challenge)
        try:
            type, id, buff = self.read_packet()
        except:
            self.handshake()
            return self.basic_stats()
        
        data = {}
        
        #I don't seem to be receiving this field...
        #data['ip'] = socket.inet_ntoa(buff[:4])[0]
        #buff = buff[4:]
        
        #Grab the first 5 string fields
        data['motd'], data['gametype'], data['map'], data['numplayers'], data['maxplayers'], buff = buff.split('\x00', 5)
        
        #Unpack a big-endian short for the port
        data['hostport'] = struct.unpack('<h', buff[:2])[0]
        
        #Grab final string component: host name
        data['hostname'] = buff[2:-1]
        
        #Encode integer fields
        for k in ('numplayers', 'maxplayers'):
            data[k] = int(data[k])

        return data
    
    def full_stats(self):
        #Pad request to 8 bytes
        self.write_packet(0, self.challenge + '\x00\x00\x00\x00')
        try:
            type, id, buff = self.read_packet()
        except:
            self.handshake()
            return self.full_stat()    
        
        #Chop off useless stuff at beginning
        buff = buff[11:]
        
        #Split around notch's silly token
        items, players = buff.split('\x00\x00\x01player_\x00\x00')
        
        #Notch wrote "hostname" where he meant to write "motd"
        items = 'motd' + items[8:] 
        
        #Encode (k1, v1, k2, v2 ..) into a dict
        items = items.split('\x00')
        data = dict(zip(items[::2], items[1::2])) 

        #Remove final two null bytes
        players = players[:-2]
        
        #Split player list
        if players: data['players'] = players.split('\x00')
        else:       data['players'] = []
        
        #Encode ints
        for k in ('numplayers', 'maxplayers', 'hostport'):
            data[k] = int(data[k])
        
        #Parse 'plugins'
        s = data['plugins']
        s = s.split(': ', 1)
        data['server_mod'] = s[0]
        if len(s) == 1:
            data['plugins'] = []
        elif len(s) == 2:
            data['plugins'] = s[1].split('; ')

        return data
                            # end query
                            # start rcon
    def close(self):
        self.r_s.close()
    
    def send(self, command):
        return self.send_real(2, command)
    
    def send_real(self, out_type, out_data):
        #Send the data
        buff = struct.pack('<iii', 10+len(out_data), 0, out_type) + out_data + "\x00\x00"
        self.r_s.send(buff)
        
        #Receive a response
        in_data = ''
        ready = True
        while ready:
            #Receive an item
            tmp_len, tmp_req_id, tmp_type = struct.unpack('<iii', self.r_s.recv(12))
            tmp_data = self.r_s.recv(tmp_len-8) #-8 because we've already read the 2nd and 3rd integer fields

            #Error checking
            if tmp_data[-2:] != '\x00\x00':
                raise Exception('protocol failure', 'non-null pad bytes')
            tmp_data = tmp_data[:-2]
            
            #if tmp_type != out_type:
            #    raise Exception('protocol failure', 'type mis-match', tmp_type, out_type)
           
            if tmp_req_id == -1:
                raise Exception('auth failure')
           
            m = re.match('^Error executing: %s \((.*)\)$' % re.escape(out_data), tmp_data)
            if m:
                raise Exception('command failure', m.group(1))
            
            #Append
            in_data += tmp_data

            #Check if more data ready...
            ready = select.select([self.r_s], [], [], 0)[0]
        
        return in_data

    def status(self):
        if self.__init__(self.q_addr,self.password) == None: ok = True
        else: ok = False
        return(ok)
    def stop(self):
        return(cleanup(self.send("stop")))
    def users(self):
        output = cleanup(self.send("list")).split(" ")
        return({'number':int(output[2]),'names':output[10:],'max':int(output[6])})
    def ls(self):
        return(self.users())
    def cmd(self,command):
        return(cleanup(self.send(command)))
    def reload(self):
        return(cleanup(self.send("reload")))
    def version(self):
        return(cleanup(self.send("version")))
    def say(self,message):
        return(cleanup(self.send("say" + str(message))))
    def save(self,mode="all"):
        return(cleanup(self.send("save-%s" % str(mode))))
    def time(self,newTime):
        return(cleanup(self.send("time set %s world" % str(newTime))))
    def day(self):
        return(cleanup(self.time("day")))
    def whitelist(self,action,user=None):
        actions = ["add","remove","reload","on","off"]
        if action not in actions: raise Exception("Unknown command %s %s" % (str(action),str(user)))
        else:
            if user: return(cleanup(self.send("whitelist %s %s" % (str(action),str(user)))))
            else: return(cleanup(self.send("whitelist %s" % str(action))))
    def night(self):
        return(self.time("night"))
    def weather(self,newWeather):
        return(cleanup(self.send("weather world %s" % str(newWeather))))
    def clear(self):
        return(cleanup(self.weather("clear")))
    def op(self,user):
        return(cleanup(self.send("op %s" % str(user))))
    def deop(self,user):
        return(self.send("deop %s" % str(user)))
    def stats(self):
        return(self.full_stats())
                            # end rcon