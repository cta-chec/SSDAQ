import sys
import os
from ssdaq.event_receivers import EventFileWriter

def main():
    import argparse


    parser = argparse.ArgumentParser(description='Start a simple event data writer.',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-l', dest='listen_port', type=str,
                        default='5555',
                        help='port for incoming event data')

    parser.add_argument('filename', type=str,
                        default='5555',
                        help='Output file name')

    args = parser.parse_args()


    data_writer = EventFileWriter(args.filename,file_enumerator='date')

    data_writer.start()

    running = True
    while(running):
        ans = input('To stop type `yes`: \n')
        if(ans == 'yes'):
            data_writer.event_listener.CloseThread()
            data_writer.running = False
            running = False

    data_writer.join()

if __name__ == "__main__":
    main()