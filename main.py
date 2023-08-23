import docker
from common import X, Y, generateISLDelay, IMAGE_NAME, NETWORK_NAME_PREFIX
from SatelliteNode import SatelliteNodeID, SatelliteNode, satellite_node_dict
from DirectionalLink import DirectionalLinkID, DirectionalLink, link_dict
from Ipv4Address import Ipv4Address


def buildSatellites():
    client = docker.from_env()

    for x in range(1, X + 1):
        for y in range(1, Y + 1):
            id = SatelliteNodeID(x, y)
            container = client.containers.run(image=IMAGE_NAME, detach=True, privileged=True, name=id.__str__())
            satellite_node_dict[id] = SatelliteNode(id, container)


def buildLinks():
    ip_subnet_cnt = 0
    client = docker.from_env()
    delay_dict = generateISLDelay()

    for x in range(1, X + 1):
        for y in range(1, Y + 1):

            # 与其右边 下边的建立双向连接
            src_node_id = SatelliteNodeID(x, y)
            link_cost = 0x3f3f3f3f
            for direction in [4, 2]:
                ip_subnet_cnt += 1
                dst_node_id = src_node_id.getNeighborIDOnDirection(direction)
                print(dst_node_id.__str__())
                forward_link_id = DirectionalLinkID(src_node_id, dst_node_id)
                backward_link_id = DirectionalLinkID(dst_node_id, src_node_id)

                src_node = satellite_node_dict[src_node_id]
                dst_node = satellite_node_dict[dst_node_id]
                src_interface_address = Ipv4Address(192, 168, ip_subnet_cnt, 1)
                dst_interface_address = src_interface_address.getNeighboringInterfaceIPAddress()

                if direction == 4:
                    link_cost = int(delay_dict[x] * 10000)
                else:
                    link_cost = int(delay_dict[0] * 10000)

                ipam_pool = docker.types.IPAMPool(
                    subnet = '192.168.%d.0/24' % ip_subnet_cnt,
                    gateway = '192.168.%d.254' % ip_subnet_cnt
                )
                ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
                network = client.networks.create(name=NETWORK_NAME_PREFIX + str(ip_subnet_cnt), driver='bridge', ipam=ipam_config)

                forward_link = DirectionalLink(src_node, dst_node, network, src_interface_address, link_cost)
                backward_link = DirectionalLink(dst_node, src_node, network, dst_interface_address, link_cost)

                link_dict[forward_link_id] = forward_link
                link_dict[backward_link_id] = backward_link


if __name__ == '__main__':
    buildSatellites()
    buildLinks()