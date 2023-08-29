import docker
import typing
from SatelliteNode import SatelliteNode, SatelliteNodeID, satellite_node_dict
from Ipv4Address import Ipv4Address


class DirectionalLinkID:
    def __init__(self, src: SatelliteNodeID, dst: SatelliteNodeID) -> None:
        self.src = src
        self.dst = dst
        
    def __str__(self):
        return self.src.__str__() + ' --> ' + self.dst.__str__()

    def __eq__(self, other):
        if not isinstance(other, DirectionalLinkID):
            raise Exception('')
        return self.src == other.src and self.dst == other.dst
    
    def __lt__(self, other):
        if self.src.__eq__(other.src):
            return self.dst.__lt__(other.dst)
        else:
            return self.src.__lt__(other.src)

    def __hash__(self):
        return hash((self.src.x, self.src.y, self.dst.x, self.dst.y))

    def generateBackwardLinkID(self):
        return DirectionalLinkID(self.dst, self.src)


class DirectionalLink:
    """
    表示单向ISL
    成员变量: 起终点、对应的docker network、起点连接到该network的接口ip地址
    注意一条单向边与其反向边要连接到同一个docker network实例
    每当新建一个DirectionalLink对象时, 都会配置容器中对应的源接口的ospf
    """

    def __init__(self, src_id: SatelliteNodeID, dst_id: SatelliteNodeID, network: docker.models.networks.Network, src_interface_address: Ipv4Address, cost: int) -> None:
        self.id = DirectionalLinkID(src_id, dst_id)
        self.src_id = src_id
        self.dst_id = dst_id
        self.network = network
        self.interface_address = src_interface_address
        self.cost = cost
        # print(self.src.id.__str__())

        self.connect()
        
        satellite_node_dict[src_id].addInterface(src_interface_address, cost)
        pass
    

    def connect(self):
        self.network.connect(container=self.src_id.__str__(), ipv4_address=self.interface_address.__str__())


    def disconnect(self):
        self.network.disconnect(container=self.src_id.__str__())


link_dict: typing.Dict[DirectionalLinkID, DirectionalLink] = {}
