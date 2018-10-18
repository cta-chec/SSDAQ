from ssdaq.core import SSEventBuilder 
import struct
import zmq
import sys
import numpy as np
import matplotlib
from matplotlib import pyplot as plt


port = sys.argv[1]
print(port)
context = zmq.Context()
sock = context.socket(zmq.SUB)
sock.setsockopt(zmq.SUBSCRIBE, b"")
sock.connect("tcp://127.0.0.101:"+port)
event_counter = np.zeros(32)
n_modules_per_event =[]
n = 0
while(True):
	data = sock.recv()
	event = SSEventBuilder.SSEvent()
	event.unpack(data)
	print("Event number %d run number %d"%(event.event_number,event.run_number))
	m = event.timestamps[:,0]>0
	# print(event.timestamps[m])
	print(np.sum(m))
	print(np.where(m)[0])
	n_modules_per_event.append(np.sum(m))
	print((event.timestamps[m][0]-event.timestamps[m])*1e-7)
	event_counter[m] += 1
	m = event_counter>0
	print(list(zip(np.where(m)[0],event_counter[m])))
	if(n>1000):
		break
	n +=1
plt.figure()
plt.hist(n_modules_per_event, 4,  facecolor='g', alpha=0.75)
plt.show()