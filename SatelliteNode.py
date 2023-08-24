import docker
import typing
import subprocess
import os
import time
from common import rescale, X, Y, HOST_HELPER_SCRIPTS_PATH, CONTAINER_HELPER_SCRIPTS_PATH, IMAGE_NAME, HOST_UDP_APP_PATH, CONTAINER_UDP_APP_PATH
from Ipv4Address import Ipv4Address


class SatelliteNodeID:
    """
    卫星的编号，由轨道号和轨内编号组成
    """

    def __init__(self, x: int, y: int):
        """
        :param x: 行号(轨内编号)  y: 列号(轨道号)
        """
        self.x = x
        self.y = y

    def __eq__(self, other):
        return isinstance(other, SatelliteNodeID) and self.x == other.x and self.y == other.y

    def __str__(self):
        return "satellite_%d_%d" % (self.x, self.y)

    def __hash__(self):
        return hash((self.x, self.y))
    
    def __lt__(self, other):
        return (self.x, self.y) < (other.x, other.y)

    def getNeighborIDOnDirection(self, direction: int):
        """
        返回该编号在对应方向上"理论上的"的邻居编号，注意这时默认全连通
        """
        if direction == 1:
            return SatelliteNodeID(rescale(self.x - 1, X), self.y)
        elif direction == 2:
            return SatelliteNodeID(rescale(self.x + 1, X), self.y)
        elif direction == 3:
            return SatelliteNodeID(self.x, rescale(self.y - 1, Y))
        elif direction == 4:
            return SatelliteNodeID(self.x, rescale(self.y + 1, Y))
        else:
            raise Exception('invalid direction!')

    def getDirectionOfNeighborID(self, neighborSatelliteID) -> int:
        """
        返回自身到对应邻居之间的方向，注意这时默认全连通
        """
        if not isinstance(neighborSatelliteID, SatelliteNodeID):
            raise Exception('parameter is not a SatelliteID!')
        else:
            if self.x == neighborSatelliteID.x:  # 相同纬度
                if neighborSatelliteID.y == rescale(self.y + 1, Y):  # neighbor在右侧
                    return 4
                elif neighborSatelliteID.y == rescale(self.y - 1, Y):  # neighbor在左侧
                    return 3
                else:
                    raise Exception("self and param are not neighbors!")
            elif self.y == neighborSatelliteID.y:  # 相同经度
                if neighborSatelliteID.x == rescale(self.x + 1, X):  # neighbor在下侧
                    return 2
                elif neighborSatelliteID.x == rescale(self.x - 1, X):  # neighbor在上侧
                    return 1
                else:
                    raise Exception("self and param are not neighbors!")
            else:
                raise Exception("self and param are not neighbors!")
            

class SatelliteNode:

    def __init__(self, id: SatelliteNodeID, container: docker.models.containers.Container) -> None:
        """
        :params id of this satellite node & its corresponding docker container
        whenever create a SatelliteNode object, frr service of its container will be started, ospf is also activated with router is configured
        then configuration of ospf interface is done when connecting to docker networks
        """
        self.id = id
        self.container = container
        self.interface_cnt = 0

        subprocess.run(['docker', 'cp', HOST_HELPER_SCRIPTS_PATH, self.id.__str__() + ':' + CONTAINER_HELPER_SCRIPTS_PATH])
        subprocess.run(['docker', 'cp', HOST_UDP_APP_PATH, self.id.__str__() + ':' + CONTAINER_UDP_APP_PATH])
        self.container.exec_run('chmod 777 -R ' + CONTAINER_HELPER_SCRIPTS_PATH + '*', privileged=True)
        self.container.exec_run('chmod 777 -R ' + CONTAINER_UDP_APP_PATH + '*', privileged=True)
 
        time.sleep(2)
        self.startFRR()  
        # copy helper scripts from local host to container


    def printIPConfig(self) -> str:
        print(self.container.exec_run('ifconfig')[1].decode())


    def startFRR(self) -> None:
        if not os.path.exists(HOST_HELPER_SCRIPTS_PATH + 'start_frr.sh'):
            raise Exception('start_frr.sh not exist!')
        
        # print(ret[1])

        router_id_str = Ipv4Address(0, 0, self.id.x, self.id.y).__str__() 
        ret = self.container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'start_frr.sh ' + router_id_str)
        # TODO: sometimes the frr is not correctly started, why?
        if ret[0] != 0:
            raise Exception('start frr failed!')
        # print(ret[1].decode())


    def configLatestOSPFInterface(self, addr: Ipv4Address, cost: int) -> None:
        if not os.path.exists(HOST_HELPER_SCRIPTS_PATH + 'config_one_ospf_interface.sh'):
            raise Exception('config_one_ospf_interface.sh not exist!')

        self.interface_cnt += 1
        interface_name = 'eth%d' % self.interface_cnt
        subnet_str = Ipv4Address(addr.ip1, addr.ip2, addr.ip3, 0).__str__() + '/24'
        
        # delay and bandwidth config
        ret = self.container.exec_run('tc qdisc add dev %s root netem delay %fms' % (interface_name, float(cost / 10)))
        # print(ret[1].decode())

        # OSPF config
        ret = self.container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'config_one_ospf_interface.sh ' + interface_name + ' ' + subnet_str + ' ' + str(cost))

        # print(ret[1].decode())
        # print('------------------------')

    
    def startReceivingUDP(self, ip: Ipv4Address) -> None:
        ret = self.container.exec_run('python3 ' + CONTAINER_UDP_APP_PATH + 'udp_receiver.py ' + ip.__str__(), stream=True)
        for line in ret[1]:
            print(line.decode())


    def startSendingUDP(self, ip: Ipv4Address) -> None:
        ret = self.container.exec_run('python3 ' + CONTAINER_UDP_APP_PATH + 'udp_sender.py ' + ip.__str__())
        print(ret[1].decode())

            
satellite_node_dict: typing.Dict[SatelliteNodeID, SatelliteNode] = {}


if __name__ == '__main__':
    client = docker.from_env()

    id = SatelliteNodeID(1, 1)
    container = client.containers.run(image=IMAGE_NAME, detach=True, privileged=True, name=id.__str__())
    satellite_node_dict[id] = SatelliteNode(id, container)
