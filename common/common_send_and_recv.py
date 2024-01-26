from SatelliteNode.SatelliteNode import SatelliteNodeID
from common.common import SIMULATION_END_TIME


PORT = 12345
RECEIVE_DURATION = SIMULATION_END_TIME + 20

DELIVERY_SRC_ID_LIST = [SatelliteNodeID(9, 3)]
# DELIVERY_SRC_ID_LIST = [SatelliteNodeID(6, 5), SatelliteNodeID(7, 5), SatelliteNodeID(8, 5), SatelliteNodeID(9, 5)]
DELIVERY_DST_ID = SatelliteNodeID(5, 5)

SEND_INTERVAL = 0.01
SENDER_NUM = len(DELIVERY_SRC_ID_LIST)
EXPECTED_RECV_CNT = SIMULATION_END_TIME / SEND_INTERVAL * SENDER_NUM

