from common.common import CONTAINER_HELPER_SCRIPTS_PATH, QUEUE_CAPACITY_PACKET, BANDWIDTH
from IPv4Address.Ipv4Address import Ipv4Address


class IPInterface:
    def __init__(self, name: str, address: Ipv4Address, cost: int) -> None:
        self.name = name
        self.address = address
        self.cost = cost
        pass


    def configOSPF(self, container):
        # delay and bandwidth config
        ret = container.exec_run('tc qdisc add dev %s root netem delay %fms rate %s limit %s' % 
                                 (self.name, float(self.cost) / 10, BANDWIDTH, QUEUE_CAPACITY_PACKET))
        # NOTE: default queue scheduling algorithm is pfifo_fast
        # after adding netem, maybe still need to add a child qdisc pfifo
        # tc qdisc add dev eth1 root netem delay 134ms rate 100Mbit limit 100
        # tc qdisc show dev eth1    -- get handle of root, for example 810c: 
        # tc qdisc add dev eth1 parent 810c:  pfifo limit 100
        # print(ret[1].decode())

        # OSPF config
        ret = container.exec_run('/bin/bash ' + CONTAINER_HELPER_SCRIPTS_PATH + 'config_one_ospf_interface.sh ' 
                                 + self.name + ' ' + self.address.__str__() + '/32' + ' ' + str(self.cost))

        # print(ret[1].decode())
        if ret[0] != 0:
            print(ret[1].decode())