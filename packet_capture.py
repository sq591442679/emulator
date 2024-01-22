from scapy.all import IP, sniff
import re
import time
import multiprocessing
from common.common import SIMULATION_END_TIME


total_bytes = 0


def ospf_lsu_callback(packet):
    global total_bytes
    if IP in packet and packet[IP].proto == 89:  # Check for OSPF LSU (type=4)
        ospf_packet = packet[IP].load

        ospf_packet_type = ospf_packet[1] if len((ospf_packet)) > 1 else None

        if (ospf_packet_type == 4):
            # print(time.time(), '\t\t', ospf_packet[1], flush=True)
            total_bytes += len(ospf_packet)


"""
returns the total size of LSU packets
unit: MBytes per second
"""
def start(result_overhead_queue: multiprocessing.Queue = None):
    interface_prefix = "br-"

    interfaces = [interface for interface in get_all_interfaces() if interface.startswith(interface_prefix)]
    # listen on docker bridges
    # print(f"Listening on interfaces: {interfaces}")

    start_time = time.time()
    
    try:
        while time.time() - start_time < SIMULATION_END_TIME:
            sniff(filter="ip proto 89", iface=interfaces, prn=ospf_lsu_callback, store=0, timeout=1)
    except KeyboardInterrupt:
        pass
    
    if result_overhead_queue is not None:
        result_overhead_queue.put(str(total_bytes / 1e6 / SIMULATION_END_TIME))
    
    return total_bytes / 1e6 / SIMULATION_END_TIME


def get_all_interfaces():
    with open("/proc/net/dev") as file:
        lines = file.readlines()[2:]
        return [re.split(r'\s*:\s*', line)[0] for line in lines]


if __name__ == "__main__":
    start()
