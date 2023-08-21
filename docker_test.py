import docker
import typing
from clean_containers import clean
from variables import IMAGE_NAME, CONTAINER_NAME_PREFIX, NETWORK_NAME_PREFIX

if __name__ == '__main__':
    print('running...')

    client = docker.from_env()
    nodes: typing.List[docker.models.containers.Container] = []
    networks: typing.List[docker.models.networks.Network] = []

    for i in range(0, 3):
        nodes.append(client.containers.run(image=IMAGE_NAME, detach=True, privileged=True, name=CONTAINER_NAME_PREFIX + str(i)))
    
    for i in range(1, 3):
        ipam_pool = docker.types.IPAMPool(
            subnet = '192.168.%d.0/24' % i,
            gateway = '192.168.%d.1' % i
        )
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        # print(ipam_config)
        networks.append(client.networks.create(name=NETWORK_NAME_PREFIX + str(i), driver='bridge', ipam=ipam_config)) 
    
    networks[0].connect('node0')
    networks[0].connect('node1')
    networks[1].connect('node1')
    networks[1].connect('node2')

    print(nodes[1].exec_run('ifconfig')[1].decode())

    try:
        print('containers running, use ctrl+C if you want to stop')
        while True:
            pass
    except KeyboardInterrupt:
        clean(IMAGE_NAME)
        
    pass