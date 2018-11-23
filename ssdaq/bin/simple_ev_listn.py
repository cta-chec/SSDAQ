import sys
import os
# from os.path import dirname as dn
# sys.path = [dn(dn(dn(os.path.realpath(__file__))))] + sys.path
from ssdaq import SSEventListener
import numpy as np
from matplotlib import pyplot as plt
import argparse

import signal
import sys

def main():

    parser = argparse.ArgumentParser(description='Start a simple event data listener.',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-l', dest='listen_port', type=str,
                        default='5555',
                        help='port for incoming event data')

    parser.add_argument('-t',dest='tm_numb',type=int,default=0,help='Set target module number for which SS data is printed out')

    args = parser.parse_args()

    ev_list = SSEventListener(args.listen_port)
    ev_list.start()

    # def signal_handler(sig, frame):
            
    #         ctrc_count +=1
        
    #         ev_list.running=False
    #         print('\npressed ctrl-C')
    #         ev_list.CloseThread()
    #         print("Closing listener")
    #         raise RuntimeError

    # signal.signal(signal.SIGINT, signal_handler)

    event_counter = np.zeros(32)
    n_modules_per_event =[]
    n = 0
    signal.alarm(0)
    ctrc_count = 0
    print('Press `ctrl-C` to stop')
    while(True):
        try:
            event = ev_list.GetEvent()
        except :
            print("\nClosing listener")
            ev_list.CloseThread()
            break
        # if(n>0):
        #     print('\033[7   A ')    
        print("Event number %d run number %d"%(event.event_number,event.run_number))
        print("Timestamp %d ns"%(event.event_timestamp))
        print("Timestamp %f s"%(event.event_timestamp*1e-9))
        m = event.timestamps[:,0]>0
        print(np.sum(m))
        print(np.where(m)[0])
        n_modules_per_event.append(np.sum(m))
        print((event.timestamps[m][0,0]*1e-9-event.timestamps[m][:,0]*1e-9))
        event_counter[m] += 1
        m = event_counter>0

        # print(list(zip(np.where(m)[0],event_counter[m])))
        # print(event.data[args.tm_numb])
        n +=1
        if(n>2000):
            break
    plt.figure()
    plt.hist(n_modules_per_event, 10,  facecolor='g', alpha=0.75)
    plt.show()
    ev_list.CloseThread()
    ev_list.join()


if __name__ == "__main__":
    main()