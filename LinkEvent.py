import typing
import numpy
import xml.dom.minidom
from xml.etree import ElementTree as et
from DirectionalLink import DirectionalLinkID, link_dict
from SatelliteNode import SatelliteNodeID
from common import LINK_DISCONNECT_TYPE, LINK_RECONNECT_TYPE, SIMULATION_END_TIME, \
                    LINK_DOWN_DURATION, WARMUP_PERIOD


class LinkEvent:

    """
    描述链路断开或恢复事件，包含开始时间与结束时间
    """

    def __init__(self, link_id: DirectionalLinkID, event_type: int, begin_time: float):
        """
        :param link: 该事件相关的单向链路
        :param eventType=1: 链路断开  eventType=2: 链路恢复
        """
        if event_type != LINK_DISCONNECT_TYPE and event_type != LINK_RECONNECT_TYPE:
            raise Exception('')
        self.link = link_id
        self.begin_time = begin_time
        self.event_type = event_type

    def __lt__(self, other):
        if not isinstance(other, LinkEvent):
            raise Exception('')
        else:
            return self.begin_time < other.begin_time

    def __str__(self):
        event = 'disconnect' if self.event_type == LINK_DISCONNECT_TYPE else 'reconnect'
        return 'link ' + self.link.__str__() + ' and its backward link ' + event + ' at ' + str(self.begin_time)

    def __eq__(self, other):
        if not isinstance(other, LinkEvent):
            raise Exception('')
        return self.link.__eq__(other.link) and self.event_type == other.event_type and self.begin_time == other.begin_time

    def __hash__(self):
        return hash({self.link, self.begin_time, self.event_type})
    

event_list: typing.List[LinkEvent] = []


def generate_events(link_failure_rate: float, delivery_src_id_list: typing.List[SatelliteNodeID], delivery_dst_id: SatelliteNodeID, file_name: str, seed=None):
    if seed != None:
        numpy.random.seed(seed)

    if link_failure_rate > 1e-6:
        poisson_lambda = link_failure_rate / (LINK_DOWN_DURATION * (1 - link_failure_rate))
        # 链路故障次数的期望，假设其服从泊松分布，则两次故障之间的时间间隔服从指数分布
        exponential_lambda = 1 / poisson_lambda
        for link_id in link_dict.keys():
            if link_id.__lt__(link_id.generateBackwardLinkID()):
                is_key_link = False

                for delivery_src_id in delivery_src_id_list:
                    if (
                            (link_id.src.__eq__(delivery_src_id) and link_id.dst.__eq__(link_id.src.getNeighborIDOnDirection(1))) \
                        or  (link_id.dst.__eq__(delivery_src_id) and link_id.src.__eq__(link_id.src.getNeighborIDOnDirection(1))) \
                        or  (link_id.src.__eq__(delivery_dst_id) and link_id.dst.__eq__(delivery_dst_id.getNeighborIDOnDirection(1))) \
                        or  (link_id.dst.__eq__(delivery_dst_id) and link_id.src.__eq__(delivery_dst_id.getNeighborIDOnDirection(1)))
                    ):
                        is_key_link = True
                
                if is_key_link == True:
                    continue

                event_time: float = WARMUP_PERIOD
                while event_time <= SIMULATION_END_TIME:
                    event_time_interval = numpy.random.exponential(scale=exponential_lambda, size=1)[0]
                    event_time += event_time_interval
                    if event_time <= SIMULATION_END_TIME:
                        event_list.append(LinkEvent(link_id, LINK_DISCONNECT_TYPE, event_time))
                        event_time += LINK_DOWN_DURATION
                        if event_time <= SIMULATION_END_TIME:
                            event_list.append(LinkEvent(link_id, LINK_RECONNECT_TYPE, event_time))
    event_list.sort()

    root = et.Element('scenario')
    for event in event_list:
        at = et.SubElement(root, 'at', attrib={
            't': ('%.3f' % event.begin_time) + 's'
        })
        if event.event_type == LINK_DISCONNECT_TYPE:
            et.SubElement(at, 'disconnect', attrib={
                'src-module': '%s' % (event.link.src.__str__()),
                'dst_module': '%s' % (event.link.dst.__str__())
            })
        elif event.event_type == LINK_RECONNECT_TYPE:
            et.SubElement(at, 'connect', attrib={
                'src-module': '%s' % (event.link.src.__str__()),
                'dst_module': '%s' % (event.link.dst.__str__())
            })
        else:
            raise Exception('')

    xml_str = et.tostring(root, encoding='utf-8')
    xml_pretty_str = xml.dom.minidom.parseString(xml_str).toprettyxml()
    with open(file_name, 'w') as f:
        f.write(xml_pretty_str)


if __name__ == '__main__':
    pass