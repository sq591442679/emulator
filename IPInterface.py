from common import CONTAINER_HELPER_SCRIPTS_PATH, QUEUE_CAPACITY_PACKET
from Ipv4Address import Ipv4Address


class IPInterface:
    def __init__(self, name: str, address: Ipv4Address, cost: int) -> None:
        self.name = name
        self.address = address
        self.cost = cost
        pass


    def configOSPF(self, container):
        # delay and bandwidth config
        ret = container.exec_run('tc qdisc add dev %s root netem delay %fms rate 10Mbit limit %s' % (self.name, float(self.cost) / 10, QUEUE_CAPACITY_PACKET))
        # print(ret[1].decode())

        # OSPF config
        ret = container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'config_one_ospf_interface.sh ' 
                                 + self.name + ' ' + self.address.__str__() + '/32' + ' ' + str(self.cost))

        # print(ret[1].decode())
        if ret[0] != 0:
            print(ret[1].decode())