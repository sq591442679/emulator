import docker
import typing
import subprocess
import os
import time
from common.common import rescale, X, Y, HOST_HELPER_SCRIPTS_PATH, CONTAINER_HELPER_SCRIPTS_PATH, \
                HOST_UDP_APP_PATH, CONTAINER_UDP_APP_PATH, \
                HOST_LOAD_AWARENESS_PATH, CONTAINER_LOAD_AWARENESS_PATH, \
                HOST_COMMON_PATH, CONTAINER_COMMON_PATH, \
                HOST_SATELLITENODE_PATH, CONTAINR_SATELLITENODE_PATH, \
                QUEUE_CAPACITY_PACKET
from common.common_load_awareness import LOFI_DELTA, ENABLE_LOAD_AWARESS
from IPv4Address.Ipv4Address import Ipv4Address
from IPInterface.IPInterface import IPInterface


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
        self.interface_dict: typing.Dict[str, IPInterface] = {}

        host_path_list = [HOST_SATELLITENODE_PATH, HOST_COMMON_PATH, HOST_HELPER_SCRIPTS_PATH, HOST_LOAD_AWARENESS_PATH, HOST_UDP_APP_PATH]
        container_path_list = [CONTAINR_SATELLITENODE_PATH, CONTAINER_COMMON_PATH, CONTAINER_HELPER_SCRIPTS_PATH, CONTAINER_LOAD_AWARENESS_PATH, CONTAINER_UDP_APP_PATH]

        for i in range(len(host_path_list)):    # copy
            host_path = host_path_list[i]
            container_path = container_path_list[i]
            subprocess.run(['docker', 'cp', host_path, self.id.__str__() + ':' + container_path], stdout=subprocess.DEVNULL)
            self.container.exec_run('chmod 777 -R ' + container_path, privileged=True)

        ret = self.container.exec_run('/bin/bash ./compile.sh', workdir=CONTAINER_LOAD_AWARENESS_PATH, privileged=True)    # compile
        ret = self.container.exec_run('chmod 777 -R ' + CONTAINER_LOAD_AWARENESS_PATH, privileged=True)
        # ret = self.container.exec_run('ls -l %s' % CONTAINER_LOAD_AWARENESS_PATH, privileged=True)
        # print(ret[1].decode())

        time.sleep(2)

        self.cleanConfig()
        self.writeLog()
        # copy helper scripts from local host to container


    def printIPConfig(self) -> str:
        print(self.container.exec_run('ifconfig')[1].decode())

    
    def cleanConfig(self):
        ret = self.container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'clean_config.sh')
        if ret[0] != 0:
            raise Exception('clean config failed!')
        

    def writeLog(self):
        if not os.path.exists(HOST_HELPER_SCRIPTS_PATH + 'log.sh'):
            raise Exception('log.sh not exist!')
        ret = self.container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'log.sh')
        if ret[0] != 0:
            raise Exception('write log failed!')


    """
    lofi_n < 0 means we use ospf
    """
    def startFRR(self, lofi_n: int) -> None:
        if not os.path.exists(HOST_HELPER_SCRIPTS_PATH + 'start_frr.sh'):
            raise Exception('start_frr.sh not exist!')

        # print('starting frr of', self.id.__str__(), flush=True)

        router_id_str = Ipv4Address(0, 0, self.id.x, self.id.y).__str__() 
        ret = self.container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'start_frr.sh ' + router_id_str + ' ' + str(lofi_n))

        if ret[0] != 0:
            raise Exception('start frr failed!')
        # print(ret[1].decode())


    def addInterface(self, addr: Ipv4Address, cost: int, direction: int) -> None:
        if not os.path.exists(HOST_HELPER_SCRIPTS_PATH + 'config_one_ospf_interface.sh'):
            raise Exception('config_one_ospf_interface.sh not exist!')

        interface_name = 'eth%d' % direction
        self.interface_dict[interface_name] = IPInterface(interface_name, addr, cost)


    def configOSPFInterfaces(self):
        for name in self.interface_dict.keys():
            interface = self.interface_dict[name]
            interface.configOSPF(self.container)


    def config_interface_down(self, direction: int):
        self.container.exec_run('ifconfig eth%d down' % direction)

    
    def config_interface_up(self, direction: int):
        self.container.exec_run('ifconfig eth%d up' % direction)

    
    def startReceivingUDP(self, shared_result_list, ip: Ipv4Address) -> None:
        ret = self.container.exec_run('python3 ' + CONTAINER_UDP_APP_PATH + 'udp_receiver.py ' + ip.__str__(), stream=True)
        for line in ret[1]:
            if len(line.decode().strip()) > 0:
                shared_result_list.append(line.decode().strip())
            # print(line.decode(), flush=True)


    def startSendingUDP(self, ip: Ipv4Address) -> None:
        ret = self.container.exec_run('python3 ' + CONTAINER_UDP_APP_PATH + 'udp_sender.py ' + ip.__str__())
        # print(ret[1].decode(), flush=True)


    def start_load_awareness(self) -> None:
        ret = self.container.exec_run('./load_awareness %d %f %s %d %d %d %d' 
                                      % (ENABLE_LOAD_AWARESS, LOFI_DELTA, QUEUE_CAPACITY_PACKET, 
                                         self.interface_dict['eth1'].cost, self.interface_dict['eth2'].cost, 
                                         self.interface_dict['eth3'].cost, self.interface_dict['eth4'].cost), 
                                         workdir=CONTAINER_LOAD_AWARENESS_PATH, privileged=True, detach=True)
        # print(ret[1].decode(), flush=True)

            
satellite_node_dict: typing.Dict[SatelliteNodeID, SatelliteNode] = {}

