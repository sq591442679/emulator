import math
import typing


IMAGE_NAME = 'satellite:changed_lsa_ttl_and_disable_dd'
CONTAINER_NAME_PREFIX = 'satellite'
NETWORK_NAME_PREFIX = 'network'

HOST_HELPER_SCRIPTS_PATH = './container_helper_scripts/'
CONTAINER_HELPER_SCRIPTS_PATH = '/container_helper_scripts/'

HOST_UDP_APP_PATH = './container_udp_applications/'
CONTAINER_UDP_APP_PATH = '/container_udp_applications/'

HOST_EVENT_GENERATOR_PATH = './container_event_generator/'
CONTAINER_EVENT_GENERATOR_PATH = '/container_event_generator/'

NUM_OF_TESTS = 1

X = 11  # 行 即每个轨道上的卫星数量
Y = 6  # 列 即轨道数

H = 780000  # 轨道高度780千米
R = 6371004  # 地球半径6371.004千米
C = 3e8  # 光速

RANDOM_SEED = 8461


def rescale(num, NUM):
    if 0 < num <= NUM:
        return num
    elif num > NUM:
        return num % NUM
    else:
        return num + NUM


def getBackwardDirection(direction: int) -> int:
    if direction not in [1, 2, 3, 4]:
        raise Exception('invalid direction')
    if direction == 1:
        return 2
    if direction == 2:
        return 1
    if direction == 3:
        return 4
    if direction == 4:
        return 3
    

def generateISLDelay() -> typing.Dict[int, float]:
    # 假设ospfRouter_1_1, ..., ospfRouter_1_6都在80.N

    ISLDelay: typing.Dict[int, float] = {}  # 轨间链路组号(0表示轨内链路) -> 时延(s)

    pi = math.pi
    latitude = math.radians(10)  # 以地心为原点，北极轴为正方向的角度
    delta_latitude = 2 * pi / X
    delta_altitude = 2 * pi / Y

    ISLDelay[0] = 2 * (H + R) * math.sin(delta_latitude / 2) / C  # 轨内链路
    for x in range(1, X + 1):
        # if abs(latitude - 0) <= pi / 2 - POLAR_RING or abs(latitude - pi) <= pi / 2 - POLAR_RING \
        #         or abs(latitude - 2 * pi) <= pi / 2 - POLAR_RING:  # 在极区内
        #     ISLDelay[x] = 0x3f3f3f3f
        # else:
        #     ISLDelay[x] = (H + R) * abs(math.sin(latitude)) * math.sin(delta_altitude / 2) / C
        ISLDelay[x] = 2 * (H + R) * abs(math.sin(latitude)) * math.sin(delta_altitude / 2) / C
        latitude += delta_latitude

    return ISLDelay


if __name__ == '__main__':
    print(generateISLDelay())