import docker
import time
from multiprocessing import Process
from threading import Thread
from common import X, Y, generateISLDelay, IMAGE_NAME, NETWORK_NAME_PREFIX, WARMUP_PERIOD, IMAGE_NAME
from SatelliteNode import SatelliteNodeID, SatelliteNode, satellite_node_dict
from DirectionalLink import DirectionalLinkID, DirectionalLink, link_dict
from Ipv4Address import Ipv4Address
from LinkEvent import generate_events
from clean_containers import clean


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
    for id in satellite_node_dict:
        print('configuring interfaces of ' + id.__str__())
        satellite_node = satellite_node_dict[id]
        satellite_node.configOSPFInterfaces()
    print('OSPF interfaces configured')


def start_sending(src_id: SatelliteNodeID, dst_id: SatelliteNodeID):
    dst_node = satellite_node_dict[dst_id]
    src_node = satellite_node_dict[src_id]
    dst_link = link_dict[DirectionalLinkID(dst_id, dst_id.getNeighborIDOnDirection(1))]
    dst_ip = dst_link.interface_address

    process_send = Process(target=src_node.startSendingUDP, args=(dst_ip,))
    process_receive = Process(target=dst_node.startReceivingUDP, args=(dst_ip,))

    print('send and receive starting...')

    process_receive.start()
    process_send.start()

    process_receive.join()
    process_send.join()

    print('send and receive completed')


if __name__ == '__main__':
    clean(IMAGE_NAME)

    time.sleep(3)

    buildSatellites()
    buildLinks()
    configOSPFInterfaces()

    print('topology successfully built with OSPF configured, wait for OSPF loading...')

    generate_events(0.05, [SatelliteNodeID(9, 3)], SatelliteNodeID(5, 5), './link_event_test.xml', seed=654)

    # time.sleep(WARMUP_PERIOD)  # wait for ospf loading

    # start_sending(SatelliteNodeID(9, 3), SatelliteNodeID(5, 5))
