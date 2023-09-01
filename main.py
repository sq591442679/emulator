import docker
import time
import typing
import json
from multiprocessing import Process, Manager
from threading import Thread
from common import X, Y, generateISLDelay, IMAGE_NAME, NETWORK_NAME_PREFIX, \
                IMAGE_NAME, LINK_FAILURE_RATE
from SatelliteNode import SatelliteNodeID, SatelliteNode, satellite_node_dict
from DirectionalLink import DirectionalLinkID, DirectionalLink, link_dict
from Ipv4Address import Ipv4Address
from clean_containers import clean


DELIVERY_SRC_ID_LIST = [SatelliteNodeID(9, 3)]
DELIVERY_DST_ID = SatelliteNodeID(5, 5)


def createSatelliteNode(client: docker.DockerClient, id: SatelliteNodeID):
    container = client.containers.run(image=IMAGE_NAME, detach=True, privileged=True, name=id.__str__())
    satellite_node_dict[id] = SatelliteNode(id, container)


def buildSatellites():
    print('starting building satellites, please wait...')

    client = docker.from_env()

    threads = []

    for x in range(1, X + 1):
        for y in range(1, Y + 1):
            id = SatelliteNodeID(x, y)
            thread = Thread(target=createSatelliteNode, args=(client, id))
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
                    link_cost = int(delay_dict[src_node_id.x] * 10000)
                else:
                    link_cost = int(delay_dict[0] * 10000)

                ipam_pool = docker.types.IPAMPool(
                    subnet = '192.168.%d.0/24' % ip_subnet_cnt,
                    gateway = '192.168.%d.254' % ip_subnet_cnt
                )
                ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
                network = client.networks.create(name=NETWORK_NAME_PREFIX + str(ip_subnet_cnt), driver='bridge', ipam=ipam_config)

                forward_link = DirectionalLink(src_node_id, dst_node_id, network, src_interface_address, link_cost)
                backward_link = DirectionalLink(dst_node_id, src_node_id, network, dst_interface_address, link_cost)

                link_dict[forward_link_id] = forward_link
                link_dict[backward_link_id] = backward_link     

    print('networks have benn built')


def configOSPFInterfaces():
    print('configuring OSPF interaces...')

    thread_list: typing.List[Thread] = []
    for id in satellite_node_dict:
        print('configuring interfaces of ' + id.__str__())
        satellite_node = satellite_node_dict[id]
        thread = Thread(target=satellite_node.configOSPFInterfaces, args=())
        thread_list.append(thread)
        thread.start()

    for thread in thread_list:
        thread.join()
        
    print('OSPF interfaces configured')
    

"""
start sending and the link disconnecting/reconnecting
"""
def startFRR():
    process_list = []

    print('starting FRR...')
    for node_id in satellite_node_dict.keys():
        node = satellite_node_dict[node_id]
        process = Process(target=node.startFRR, args=())
        process.start()
        process_list.append(process)

    for process in process_list:
        process.join()


def startSimulation():
    dst_node = satellite_node_dict[DELIVERY_DST_ID]
    src_node_list = [satellite_node_dict[i] for i in DELIVERY_SRC_ID_LIST]
    process_list: typing.List[Process] = []
    manager = Manager()
    shared_event_list = manager.list()

    dst_link = link_dict[DirectionalLinkID(DELIVERY_DST_ID, DELIVERY_DST_ID.getNeighborIDOnDirection(1))]
    dst_ip = dst_link.interface_address

    process_receive = Process(target=dst_node.startReceivingUDP, args=(dst_ip,))
    process_list.append(process_receive)

    for src_node in src_node_list:
        process_send = Process(target=src_node.startSendingUDP, args=(dst_ip,))
        process_list.append(process_send)

    for id in satellite_node_dict.keys():
        node = satellite_node_dict[id]
        process_event_generator = Process(target=node.startEventGenerating, args=(shared_event_list, LINK_FAILURE_RATE, node.id.__hash__()))
        process_list.append(process_event_generator)

    for process in process_list:
        process.start()

    for process in process_list:
        process.join()

    print('send and receive completed')
    json_list = [json.loads(event) for event in shared_event_list]
    json_list.sort(key=lambda x: x["sim_time"])
    # shared_event_list.sort()
    with open('./events.txt', 'w') as f:
        for event in json_list:
            print(event, file=f)


if __name__ == '__main__':
    clean(IMAGE_NAME)

    time.sleep(3)

    buildSatellites()
    buildLinks()
    configOSPFInterfaces()

    startFRR()

    startSimulation()

    clean(IMAGE_NAME)
