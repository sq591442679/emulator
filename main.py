import docker
import time
import typing
import csv
import json
from multiprocessing import Process, Manager, Lock, Queue
import subprocess
import os
from threading import Thread
from common.common import X, Y, generateISLDelay, getBackwardDirection, NETWORK_NAME_PREFIX, \
                NUM_OF_TESTS, WARMUP_PERIOD, LINK_DOWN_DURATION, SIMULATION_END_TIME
from common.common_send_and_recv import DELIVERY_DST_ID, DELIVERY_SRC_ID_LIST
from common.common_load_awareness import ENABLE_LOAD_AWARESS
from SatelliteNode.SatelliteNode import SatelliteNodeID, SatelliteNode, satellite_node_dict
from DirectionalLink.DirectionalLink import DirectionalLinkID, DirectionalLink, link_dict
from IPv4Address.Ipv4Address import Ipv4Address
from clean_containers import clean
import packet_capture
import random


def createSatelliteNode(client: docker.DockerClient, id: SatelliteNodeID, image_name: str):
    container = client.containers.run(image=image_name, detach=True, privileged=True, name=id.__str__())
    satellite_node_dict[id] = SatelliteNode(id, container)


def buildSatellites(image_name: str):
    print('starting building satellites, please wait...')

    client = docker.from_env()

    threads = []

    for x in range(1, X + 1):
        for y in range(1, Y + 1):
            id = SatelliteNodeID(x, y)
            thread = Thread(target=createSatelliteNode, args=(client, id, image_name))
            thread.start()
            threads.append(thread)

    for thread in threads:
            thread.join()
    
    # print("key: ", satellite_node_dict.keys())
    print('satellites have been built')


def buildLinks():
    print('starting building networks, please wait...')

    ip_subnet_cnt = 0
    client = docker.from_env()
    delay_dict = generateISLDelay()

    for x in range(1, X + 1):
        for y in range(1, Y + 1):
            # 与其右边 下边的建立双向连接
            # NOTE in this step, networks are created but not connected
            # this is in order to ensure eth1 of a container is really the upper intf
            src_node_id = SatelliteNodeID(x, y)
            for direction in [4, 2]:
                ip_subnet_cnt += 1
                
                dst_node_id = src_node_id.getNeighborIDOnDirection(direction)
                # print(src_node_id.__str__())
                forward_link_id = DirectionalLinkID(src_node_id, dst_node_id)
                backward_link_id = DirectionalLinkID(dst_node_id, src_node_id)

                src_interface_address = Ipv4Address(192, 168, ip_subnet_cnt, 1)
                dst_interface_address = src_interface_address.getNeighboringInterfaceIPAddress()

                link_cost = 0x3f3f3f3f

                if direction == 4:
                    link_cost = int(round(delay_dict[src_node_id.x] * 10000))   # cost is defined as delay (ms) * 10
                else:
                    link_cost = int(round(delay_dict[0] * 10000))

                ipam_pool = docker.types.IPAMPool(
                    subnet = '192.168.%d.0/24' % ip_subnet_cnt,
                    gateway = '192.168.%d.254' % ip_subnet_cnt
                )
                ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
                network = client.networks.create(name=NETWORK_NAME_PREFIX + str(ip_subnet_cnt), driver='bridge', ipam=ipam_config)

                forward_link = DirectionalLink(src_node_id, dst_node_id, network, 
                                               src_interface_address, link_cost, direction)
                backward_link = DirectionalLink(dst_node_id, src_node_id, network, 
                                                dst_interface_address, link_cost, getBackwardDirection(direction))

                link_dict[forward_link_id] = forward_link
                link_dict[backward_link_id] = backward_link 

    # in this step the nwtworks are connected to containers
    # the intf to the first connected network is eth1, and so on
    for x in range(1, X + 1):
        for y in range(1, Y + 1):
            src_node_id = SatelliteNodeID(x, y)
            for direction in [1, 2, 3, 4]:
                dst_node_id = src_node_id.getNeighborIDOnDirection(direction)
                forward_link_id = DirectionalLinkID(src_node_id, dst_node_id)
                link_dict[forward_link_id].connect()

    print('networks have been built')


def configOSPFInterfaces():
    print('configuring OSPF interaces...')

    thread_list: typing.List[Thread] = []
    for id in satellite_node_dict:
        # print('configuring interfaces of ' + id.__str__())
        satellite_node = satellite_node_dict[id]
        thread = Thread(target=satellite_node.configOSPFInterfaces, args=())
        thread_list.append(thread)
        thread.start()

    for thread in thread_list:
        thread.join()
        
    print('OSPF interfaces configured')
    

def startFRR(lofi_n: int):
    process_list = []

    print('starting FRR...')
    for node_id in satellite_node_dict.keys():
        node = satellite_node_dict[node_id]
        process = Process(target=node.startFRR, args=(lofi_n, ))
        process.start()
        process_list.append(process)

    for process in process_list:
        process.join()
    print('FRR started')


"""
start sending and the link disconnecting/reconnecting
"""
def startSimulation(link_failure_rate: float) -> typing.Dict:
    dst_node = satellite_node_dict[DELIVERY_DST_ID]
    src_node_list = [satellite_node_dict[i] for i in DELIVERY_SRC_ID_LIST]
    process_list: typing.List[Process] = []
    manager = Manager()
    shared_result_list = manager.list()
    result_overhead_queue = Queue()

    dst_link_id = DirectionalLinkID(DELIVERY_DST_ID, DELIVERY_DST_ID.getNeighborIDOnDirection(1))
    dst_link = link_dict[dst_link_id]
    dst_ip = dst_link.interface_address

    process_receive = Process(target=dst_node.startReceivingUDP, args=(shared_result_list, dst_ip,))
    process_list.append(process_receive)

    for src_node in src_node_list:
        process_send = Process(target=src_node.startSendingUDP, args=(dst_ip,))
        process_list.append(process_send)

    lock = Lock()
    link_id_set_for_event: typing.Set[DirectionalLinkID] = set()
    for id in link_dict.keys():
        if id.__lt__(id.generateBackwardLinkID()) and not id.__eq__(dst_link_id):
            link_id_set_for_event.add(id)
    process_event_generator = Process(target=link_event_generator, args=(link_id_set_for_event, lock, link_failure_rate))  # no random seed
    process_list.append(process_event_generator)

    process_capture = Process(target=packet_capture.start, args=(result_overhead_queue, ))
    process_list.append(process_capture)

    for process in process_list:
        process.start()

    for process in process_list:
        process.join()

    print('send and receive completed')

    # event_file_path = result_prefix + 'events.json'
    # if len(shared_event_list) > 0:
    #     json_list = [json.loads(event) for event in shared_event_list]
    #     json_list.sort(key=lambda x: x["sim_time"])
    #     shared_event_list.sort()
    #     with open(event_file_path, 'a') as f:
    #         json.dump(json_list, f, indent=None)
    # else:
    #     with open(event_file_path, 'a') as f:
    #         print('', file=f)

    # ret = json.loads(shared_result_list[0])
    # ret['overhead'] = result_overhead_queue.get()
    
    # return ret


"""
change the generation of link failure event
past: each container generates interface failure independently in ./container_evnet_generator/
now: centralized link failure generation in main.py
"""
def link_event_generator(link_id_set_for_event: typing.Set[DirectionalLinkID], lock: Lock, link_failure_rate: float) -> None:
    if abs(link_failure_rate - 0) < 1e-6:
        return

    poisson_lambda = link_failure_rate / (LINK_DOWN_DURATION * (1 - link_failure_rate))
    start_time = time.time()

    for link_id in link_id_set_for_event:   # init the first link down moment
        link = link_dict[link_id]
        sim_time_interval = random.expovariate(poisson_lambda)
        link.down_moment = sim_time_interval

    flag = False
    while True:
         if (flag):
             break
         for link_id in link_id_set_for_event:
            link = link_dict[link_id]
            src = link_id.src
            dst = link_id.dst
            direction = src.getDirectionOfNeighborID(dst)
            backward_direction = dst.getDirectionOfNeighborID(src)

            current_sim_time = time.time() - start_time

            if current_sim_time <= SIMULATION_END_TIME:
                if link.is_down and current_sim_time <= link.down_moment + LINK_DOWN_DURATION:
                    # link is in down state
                    continue
                elif link.is_down and current_sim_time > link.down_moment + LINK_DOWN_DURATION:
                    # link should recover
                    with lock:
                        print(
                            '{"sim_time": %.3f, "link": "%s <--> %s", "type": "up"}'
                            % (current_sim_time, link_id.src, link_id.dst),
                            flush=True
                        )
                        satellite_node_dict[src].config_interface_up(direction)
                        satellite_node_dict[dst].config_interface_up(backward_direction)
                    link.is_down = False
                    sim_time_interval = random.expovariate(poisson_lambda)
                    link.down_moment = current_sim_time + sim_time_interval # set the next link down moment
                elif not link.is_down and current_sim_time > link.down_moment:
                    # link should turned to down
                    with lock:
                        print(
                            '{"sim_time": %.3f, "link": "%s <--> %s", "type": "down"}'
                            % (current_sim_time, link_id.src, link_id.dst),
                            flush=True
                        )
                        satellite_node_dict[src].config_interface_down(direction)
                        satellite_node_dict[dst].config_interface_down(backward_direction)    
                    link.is_down = True
                else:
                    continue

                current_sim_time = time.time() - start_time
                if current_sim_time >= SIMULATION_END_TIME:
                    break
            else:   # sim time exceeded, loop should stop
                flag = True  


"""
this function will be called whether ENABLE_LOAD_AWARENESS is set
"""
def start_load_awareness(image_name: str):
    if image_name == 'locksoyev/lofi_satellite:ospf':
        print('using ospf, do not config load awareness')
    else:
        for id in satellite_node_dict.keys():
            satellite_node_dict[id].start_load_awareness()
        print('load awareness configured')


"""
only start containers & networks,
and run the routing protocol,
but no UDP sending and event generating.
used for tests
"""
def dry_run(image_name: str, lofi_n: int):
    clean(image_name)

    time.sleep(3)

    buildSatellites(image_name)
    buildLinks()
    configOSPFInterfaces()

    startFRR(lofi_n)
    # start_load_awareness(image_name)

    time.sleep(WARMUP_PERIOD)

    # startSimulation(0.2)


def main():
    sudo_uid = os.environ.get('SUDO_UID')

    if sudo_uid is None:
        print('need to have root permission, use sudo instead')
        return
    
    is_dry_run = True

    if (is_dry_run):
        dry_run('ospf:latest', -1)
    else:
        # link_failure_rate_list = [0, 0.05, 0.1, 0.15, 0.2]
        link_failure_rate_list = [0.05]
        # link_failure_rate_list = [0.05, 0.15]
        # image_name_list = ['locksoyev/lofi_satellite:n_%d' % i for i in range(0, 6)] + ['locksoyev/lofi_satellite:ospf']
        image_name_list = ['locksoyev/lofi_satellite:n_0']

        # for link_failure_rate in link_failure_rate_list:
        #     for image_name in image_name_list:
        #         if ENABLE_LOAD_AWARESS:
        #             result_prefix = './results/ENABLE_LOAD_AWARESS/%s/%.02f/' % (image_name.split(':')[-1], link_failure_rate)
        #         else:
        #             result_prefix = './results/NO_LOAD_AWARESS/%s/%.02f/' % (image_name.split(':')[-1], link_failure_rate)
        #         result_file_path = result_prefix + 'result.csv'  

        #         header = ['cnt', 'drop rate', 'delay', 'overhead']

        #         if not os.path.exists(result_prefix):
        #             os.makedirs(result_prefix)

        #         with open(result_file_path, mode='w', newline='') as f:
        #             writer = csv.writer(f)
        #             writer.writerow(header)
        #             f.flush()

        #             avg_drop_rate = 0.0
        #             avg_delay = 0.0
        #             avg_overhead = 0.0

        #             for i in range(1, NUM_OF_TESTS + 1):
        #                 print('link failure rate: %f, image name:%s, test: %d' % (link_failure_rate, image_name, i))
                        

        #                 # kernel_dmesg_file = "/home/sqsq/Desktop/kernel.log"
        #                 # sudo_password = 'shanqian'
        #                 # os.system(f"echo '{sudo_password}' | sudo -S dmesg -c > /dev/null")  # clear the ring buffer and abandon the output
        #                 # time.sleep(1)
        #                 # process_dmesg = subprocess.Popen(f"echo '{sudo_password}' | sudo -S dmesg --follow > '{kernel_dmesg_file}'", shell=True)

        #                 clean(image_name)

        #                 time.sleep(3)

        #                 buildSatellites(image_name)
        #                 buildLinks()
        #                 configOSPFInterfaces()

        #                 startFRR()
        #                 start_load_awareness(image_name)

        #                 time.sleep(WARMUP_PERIOD)  # wait for OSPF convergence

        #                 start_time = time.time()
        #                 ret = startSimulation(link_failure_rate)
        #                 end_time = time.time()

        #                 writer.writerow([i, ret['drop rate'], ret['delay'], ret['overhead']])
        #                 f.flush()

                        
        #                 print(i, ret, flush=True)
        #                 print('simulation elapsed time:%.2f' % (end_time - start_time))

        #                 avg_drop_rate += float(ret['drop rate'].strip('%'))
        #                 avg_delay += float(ret['delay'])
        #                 avg_overhead += float(ret['overhead'])

        #                 clean(image_name)    
        #                 # process_dmesg.terminate()

        #                 print('----------------------')
        #                 time.sleep(1)

        #             avg_drop_rate /= NUM_OF_TESTS
        #             avg_delay /= NUM_OF_TESTS
        #             avg_overhead /= NUM_OF_TESTS
        #             writer.writerow(['avg', '%.2f%%' % avg_drop_rate, '%.2f' % avg_delay, '%.2f' % avg_overhead])


if __name__ == '__main__':
    main()