import socket
import sys
import time
import pickle
from udp_common import *

if __name__ == '__main__':
    send_interval = SEND_INTERVAL
    target_ip = str(sys.argv[1])
    target_port = PORT
    total_send_duration = SIMULATION_DURATION

    cnt = 0

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print('wait for OSPF loading', flush=True)
    time.sleep(WARMUP_PERIOD)

    print('sending UDP to ' + target_ip, flush=True)

    start_time = time.time()

    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time >= total_send_duration:
            break

        cnt += 1
        data_dict = {
            'cnt': cnt,
            'time': current_time
        }
        data_bytes = pickle.dumps(data_dict)
        udp_socket.sendto(data_bytes, (target_ip, target_port))

        time.sleep(send_interval)

    udp_socket.close()

    print('sending stopped')
