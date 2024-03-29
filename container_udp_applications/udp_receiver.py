import socket
import sys
import pickle
import time
from common.common_send_and_recv import PORT, RECEIVE_DURATION, EXPECTED_RECV_CNT

if __name__ == '__main__':
    local_ip = str(sys.argv[1])
    local_port = PORT

    total_receive_duration = RECEIVE_DURATION

    receive_cnt = 0
    avg_delay = 0

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((local_ip, local_port))
    udp_socket.settimeout(1.0)

    # print('receiving UDP on ' + local_ip, flush=True)

    start_time = time.time()

    while True:
        try:
            current_time = time.time()
            if current_time - start_time > total_receive_duration:
                break

            data_bytes, addr = udp_socket.recvfrom(2048)
            received_data = pickle.loads(data_bytes)

            # print(received_data, flush=True)  # NOTE THE FLUSH

            avg_delay += (time.time() - received_data['real_time']) * 1000  # unit: ms
            receive_cnt += 1
        except socket.timeout:
            continue

    if receive_cnt == 0:
        avg_delay = 0x3f3f3f3f
    else:
        avg_delay /= receive_cnt
    print('{"drop rate": "%.1f%%", "delay": "%.1f"}' % ((1 - receive_cnt / EXPECTED_RECV_CNT) * 100, avg_delay), flush=True)

    # print('receiving stopped', flush=True)
