import socket
import sys
import pickle
import time
from udp_common import *

if __name__ == '__main__':
    local_ip = str(sys.argv[1])
    local_port = PORT

    total_receive_duration = RECEIVE_DURATION

    expected_cnt = SIMULATION_DURATION / SEND_INTERVAL
    receive_cnt = 0
    avg_delay = 0

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((local_ip, local_port))
    udp_socket.settimeout(1.0)

    print('receiving UDP on ' + local_ip, flush=True)

    start_time = time.time()

    while True:
        try:
            current_time = time.time()
            if current_time - start_time > total_receive_duration:
                break

            data_bytes, addr = udp_socket.recvfrom(1024)
            received_data = pickle.loads(data_bytes)

            print(received_data, flush=True)  # NOTE THE FLUSH

            avg_delay += (time.time() - received_data['time']) * 1000  # unit: ms
            receive_cnt += 1
        except socket.timeout:
            continue

    avg_delay /= receive_cnt
    print('received %d/%d packets, avg delay:%.1fms' % (receive_cnt, int(SIMULATION_DURATION / SEND_INTERVAL), avg_delay), flush=True)

    print('receiving stopped', flush=True)
