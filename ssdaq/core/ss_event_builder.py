import asyncio
import struct
import numpy as np
from datetime import datetime
READOUT_LENGTH = 64*2+2*8 #64 2-byte channel amplitudes and 2 8-byte timestamps

class SlowSignalDataProtocol(asyncio.Protocol):
    def __init__(self,loop,log,relaxed_ip_range, packet_debug_stream_file = None):
        self._buffer = asyncio.Queue()
        self.loop = loop
        self.log = log.getChild('SlowSignalDataProtocol')
        self.relaxed_ip_range = relaxed_ip_range
        if(packet_debug_stream_file != None):
            self.log.info('Opening a packet_debug_stream_file at %s'%packet_debug_stream_file)
            self.packet_debug_stream_file = open(packet_debug_stream_file,'w')
            self.packet_debug_stream = True
        else:
            self.packet_debug_stream = False

    def connection_made(self, transport):
        #self.log.info('Connected to port')
        self.transport = transport

    def datagram_received(self, data, addr):
        
        if(len(data)%(READOUT_LENGTH) != 0):
            self.log.warn("Got unsuported packet size, skipping packet")
            #self.log.info("Bad package came from %s:%d"%tuple(data[0]))
            return
        nreadouts = int(len(data)/(READOUT_LENGTH))

        #getting the module number from the last two digits of the ip
        ip = addr[0]
        module_nr = int(ip[-ip[::-1].find('.'):])%100
        if(module_nr>31 and self.relaxed_ip_range):
            #ensure that the module number is in the allowed range
            #(mostly important for local or standalone setups simulations)
            module_nr = module_nr%32
            #self.log.debug('Got data from ip %s which is outsie the allowed range'%ip)
        elif(module_nr>31):
            self.log.error('Error: got packets from ip out of range:')
            self.log.error('   %s'%ip)
            self.log.error('This can be supressed if relaxed_ip_range=True')
            raise RuntimeError
            
        #self.log.debug("Got data from %s assigned to module %d"%(str(ip),module_nr))
        for i in range(nreadouts):
            unpacked_data = struct.unpack_from('>Q32HQ32H',data,i*(READOUT_LENGTH))
            
            self.loop.create_task(self._buffer.put((module_nr,unpacked_data[0],unpacked_data)))
        if(self.packet_debug_stream):
                self.packet_debug_stream_file.write('%d  %d  %d\n'%(unpacked_data[0],int(datetime.utcnow().timestamp()*1e9) , module_nr))
        #self.log.debug('Front buffer length %d'%(self._buffer.qsize()))
        if(self._buffer.qsize()>1000):
            self.log.warning('Front buffer length %d'%(self._buffer.qsize()))

class SSEvent(object):
    """
    A class representing a slow signal event
    """

    def __init__(self, timestamp=0, event_number = 0, run_number = 0):
                
        self.event_number = event_number
        self.run_number = run_number
        self.event_timestamp = timestamp
        self.data = np.empty((32,64))
        self.data[:] = np.nan
        #store also the time stamps for the individual readings 
        #two per TM (primary and aux)
        self.timestamps = np.zeros((32,2),dtype=np.uint64)
    
    def pack(self):
        '''
        Convinience method to pack the event into a bytestream
        '''
        d_stream = bytearray(struct.pack('3Q',
                            self.event_number,
                            self.run_number,
                            self.event_timestamp))

        d_stream.extend(self.data.tobytes())
        d_stream.extend(self.timestamps.tobytes())
        return d_stream

    def unpack(self,byte_stream):
        '''
        Unpack a bytestream into an event
        '''
        self.event_number, self.run_number,self.event_timestamp = struct.unpack_from('3Q',byte_stream,0)
        self.data = np.frombuffer(byte_stream[8*3:8*(3+2048)],dtype=np.float64).reshape(32,64)
        self.timestamps = np.frombuffer(byte_stream[8*(3+2048):8*(3+2048+64)],dtype=np.uint64).reshape(32,2)

class PartialEvent:
    int_counter = 0
    def __init__(self,tm_num,data):
        self.data = [None]*32
        self.data[tm_num] = data
        self.timestamp =data[0]
        self.tm_parts = [0]*32
        self.tm_parts[tm_num] = 1
        PartialEvent.int_counter += 1
        self.event_number =  PartialEvent.int_counter   
    def add_part(self, tm_num, data):
        self.data[tm_num] = data
        self.tm_parts[tm_num] = 1

class SSEventBuilder:
    """ 
    Slow signal event builder. Constructs 
    slow signal events from data packets recieved from 
    Target Modules.
    """
    def __init__(self, relaxed_ip_range=False, 
                       event_tw = 0.0001*1e9, 
                       listen_ip = '0.0.0.0',
                       listen_port = 2009,
                       buffer_length = 1000,
                       buffer_time = 10*1e9,
                       publishers = [],
                       packet_debug_stream_file = None):
        from ssdaq import sslogger
        import zmq
        import zmq.asyncio
        from distutils.version import LooseVersion
        if(LooseVersion('17')>LooseVersion(zmq.__version__)):
            zmq.asyncio.install()
        import inspect
        self.log = sslogger.getChild('SSEventBuilder')
        self.relaxed_ip_range = relaxed_ip_range
        # self.listening = 
        # self.building_events = 
        # self.publishing_events = 

        

        #settings 
        self.event_tw = int(event_tw)
        self.listen_addr = (listen_ip, listen_port)
        self.buffer_len = buffer_length
        self.buffer_time = buffer_time
        self.packet_debug_stream_file = packet_debug_stream_file 
        
        #counters
        self.nprocessed_packets = 0
        self.nconstructed_events = 0
        self.event_count = 1
        self.packet_counter = {}
        self.event_counter = {}

        self.loop = asyncio.get_event_loop()
        self.corrs = [self.builder(),self.handle_commands()]
        
        #controlers
        self.publish_events = True

        #buffers
        self.inter_buff = []
        self.partial_ev_buff = asyncio.queues.collections.deque(maxlen=self.buffer_len)
        
        self.publishers = publishers 
        #Giving the event loop to the publishers     
        for p in self.publishers:
            p.give_loop(self.loop)

        #setting up communications socket
        self.context = zmq.asyncio.Context()    
        self.com_sock = self.context.socket(zmq.REP)
        self.com_sock.bind("ipc:///tmp/ssdaq-control")

        #Introspecting to find all methods that
        #handle commands
        method_list = inspect.getmembers(self, predicate=inspect.ismethod)
        self.cmds = {}
        for method in method_list:
            if(method[0][:4] == 'cmd_'):
                self.cmds[method[0][4:]] = method[1]

    def run(self):
        #self.log.info('Settting up listener at %s:%d'%(tuple(self.listen_addr)))
        listen = self.loop.create_datagram_endpoint(
        lambda :SlowSignalDataProtocol(self.loop,self.log,self.relaxed_ip_range, packet_debug_stream_file = self.packet_debug_stream_file), 
        local_addr=self.listen_addr)
        
        transport, protocol = self.loop.run_until_complete(listen)
        self.ss_data_protocol = protocol
        #self.log.info('Number of publishers registered %d'%len(self.publishers))
        for c in self.corrs:
            self.loop.create_task(c)

        try:
            self.loop.run_forever()
        except:
            pass
        self.loop.close()

    def cmd_reset_ev_count(self,arg):
        #self.log.info('Event count has ben reset')
        self.event_count = 1
        return b'Event count reset'
    
    def cmd_set_publish_events(self,arg):
        if(arg[0] == 'false' or arg[0] == 'False'):
            self.publish_events = False
            #self.log.info('Pause publishing events')
            return b'Paused event publishing'
        elif(arg[0] == 'true' or arg[0] == 'True'):
            self.publish_events = True
            #self.log.info('Pause publishing events')
            return b'Unpaused event publishing'
        else:
            #self.log.info('Unrecognized command for command `set_publish_events` \n    no action taken')
            return ('Unrecognized arg `%s` for command `set_publish_events` \nno action taken'%arg[0]).encode('ascii') 

    async def handle_commands(self):
        '''
        This is the server part of the simulation that handles 
        incomming commands to control the simulation
        '''
        while(True):
            cmd = await self.com_sock.recv()
            #self.log.info('Handling incoming command %s'%cmd.decode('ascii'))
            cmd = cmd.decode('ascii').split(' ')
            if(cmd[0] in self.cmds.keys()):
                reply = self.cmds[cmd[0]](cmd[1:])
            else:
                reply = b"Error, No command `%s` found."%(cmd[0])
                #self.log.info('Incomming command `%s` not recognized')
            self.com_sock.send(reply)


    async def builder(self):
        n_packets = 0
        #self.log.info('Empty socket buffer before starting event building')
        packet = await self.ss_data_protocol._buffer.get()
        got_packet = True
        while(got_packet):
            got_packet = False
            #self.log.info('Thrown away %d packets in buffer before start'%n_packets)
            try:
                while(True):
                    await asyncio.wait_for(self.ss_data_protocol._buffer.get(), timeout=0)
                    n_packets +=1
                    got_packet = True
            except:
                pass
        #self.log.info('Thrown away %d packets in buffer before start'%n_packets)
        #self.log.info('Starting event build loop')
        packet = await self.ss_data_protocol._buffer.get()
        self.partial_ev_buff.append(PartialEvent(packet[0], packet[2]))
        while(True):
            packet = await self.ss_data_protocol._buffer.get()
            #self.log.debug('Got packet from front buffer with timestamp %f and tm id %d'%(packet[1]*1e-9,packet[0]))
            pe = self.partial_ev_buff[-1]
            dt = (pe.timestamp - packet[1])

            if(abs(dt) < self.event_tw  and pe.tm_parts[packet[0]] == 0):#
                self.partial_ev_buff[-1].add_part(packet[0], packet[2])
                #self.log.debug('Packet added to the tail of the buffer')
            
            elif(dt<0):
                self.partial_ev_buff.append(PartialEvent(packet[0], packet[2]))
                #self.log.debug('Packet added to a new event at the tail of the buffer')
            
            else:
                if(self.partial_ev_buff[0].timestamp - packet[1]>0):
                    self.partial_ev_buff.appendleft(PartialEvent(packet[0], packet[2]))
                    #self.log.debug('Packet added to a new event at the head of the buffer')   
                else:
                    #self.log.debug('Finding right event in buffer')
                    found = False
                    for i in range(len(self.partial_ev_buff)-1,0,-1):
                        pe = self.partial_ev_buff[i]
                        dt = (pe.timestamp - packet[1])

                        if(abs(dt)< self.event_tw):#
                            if(pe.tm_parts[packet[0]]==1):
                                self.log.warning('Dublette packet with timestamp %f and tm id %d with cpu timestamp %f'%(packet[1]*1e-9,packet[0],packet[2][33]*1e-9))
                            self.partial_ev_buff[i].add_part(packet[0], packet[2]) 
                            #self.log.debug('Packet added to %d:th event in buffer'%i)
                            found =True
                            break
                        elif(dt<0):
                            self.partial_ev_buff.insert(i+1,PartialEvent(packet[0], packet[2]))
                            found = True
                            break
                            
                    if(not found):
                        self.log.warning('No partial event found for packet with timestamp %f and tm id %d'%(packet[1]*1e-9,packet[0]))
                        #self.log.info('Newest event timestamp %f'%(self.partial_ev_buff[-1].timestamp*1e-9))
                        #self.log.info('Next event timestamp %f'%(self.partial_ev_buff[0].timestamp*1e-9))     
            if(abs(float(self.partial_ev_buff[-1].timestamp) - float(self.partial_ev_buff[0].timestamp))>(self.buffer_time)):
                #self.log.debug('First %f and last %f timestamp in buffer '%(self.partial_ev_buff[0].timestamp*1e-9,self.partial_ev_buff[-1].timestamp*1e-9))
                event = self.build_event(self.partial_ev_buff.popleft())               
                #   if(self.nconstructed_events%10==0):
                    # for d in self.partial_ev_buff:
                        # print(d.timestamp*1e-9,d.timestamp,d.event_number, d.tm_parts)
                    #self.log.info('Built event %d'%self.nconstructed_events)
                    #self.log.info('Newest event timestamp %f'%(self.partial_ev_buff[-1].timestamp*1e-9))
                    #self.log.info('Next event timestamp %f'%(self.partial_ev_buff[0].timestamp*1e-9))
                    #self.log.info('Last timestamp dt %f'%((self.partial_ev_buff[-1].timestamp - self.partial_ev_buff[0].timestamp)*1e-9))
                    #self.log.info('Number of TMs participating %d'%(sum(event.timestamps[:,0]>0)))
                    #self.log.info('Buffer lenght %d'%(len(self.partial_ev_buff)))
                #self.log.debug('Built event %d'%self.nconstructed_events)
                if(self.publish_events):
                    for pub in self.publishers:
                        pub.publish(event)
    
    def build_event(self,pe):
        #construct event
        event = SSEvent(int(pe.timestamp),self.event_count,0)
        for i,tmp_data in enumerate(pe.data):
            if(tmp_data == None):
                continue
            if(i in self.event_counter):
                self.event_counter[i] += 1
            else:
                self.event_counter[i] = 1
            #put data into a temporary array of uint type
            tmp_array = np.empty(64,dtype=np.uint64)
            tmp_array[:32] = tmp_data[1:33]
            tmp_array[32:] = tmp_data[34:]
            
            #converting counts to mV
            m = tmp_array < 0x8000
            tmp_array[m] += 0x8000
            tmp_array[~m] = tmp_array[~m]&0x7FFF
            event.data[i] = tmp_array* 0.03815*2.
            #get the readout time stamps for the primary and aux
            event.timestamps[i][0]=tmp_data[0]
            event.timestamps[i][1]=tmp_data[33]
        self.nconstructed_events += 1
        self.event_count += 1
        return event    

class ZMQEventPublisher():
    ''' Slow signal event publisher
        
        Publishes event on a TCP/IP socket using the zmq PUB-SUB protocol.
        
        Args:
            ip (str):   the name (ip) interface which the events are published on
            port (int): the port number of the interface which the events are published on
        Kwargs:
            name (str): The name of this instance (usefull for logging)
            logger:     An instance of a logger to inherit from
            mode (str): The mode of publishing. Possible modes ('local','outbound', 'remote')

        The three different modes defines how the socket is setup for different use cases.

            * 'local' this is the normal use case where events are published on localhost
                and ip should be '127.x.x.x'
            * 'outbound' is when the events are published on an outbound network interface of 
                the machine so that remote clients can connect to the machine to receive the events. 
                In this case ip is the ip address of the interface on which the events should be published
            * 'remote' specifies that the given ip is of a remote machine to which the events should be sent to.   


    '''
    def __init__(self,ip,port,name='ZMQEventPublisher',logger=None, mode = 'local'):
        '''Slow signal event publisher
        '''

        import zmq
        import logging
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.PUB)
        con_str = 'tcp://%s:'%ip+str(port)
        
        if(mode == 'local' or mode == 'outbound'):
            self.sock.bind(con_str)
        
        if(mode == 'outbound' or mode == 'remote'):
            self.sock.connect(con_str)
        
        if(logger==None):
            self.log = logging.getLogger('ssdaq.%s'%name)
        else:
            self.log = logger.getChild(name)
        #self.log.info('Initialized event publisher on: %s'%con_str)
    
    def give_loop(self,loop):
        self.loop = loop

    def publish(self,event):
        self.sock.send(event.pack())

if(__name__ == "__main__"):
    from ssdaq import sslogger
    import logging
    import os
    from subprocess import call
    call(["taskset","-cp", "0,4","%s"%(str(os.getpid()))])
    sslogger.setLevel(logging.INFO)
    zmq_pub = ZMQEventPublisher('127.0.0.101',5555) 
    ev_builder = SSEventBuilder(publishers= [zmq_pub])
    ev_builder.run()

