import docker
import typing
import subprocess
from clean_containers import clean
from common import IMAGE_NAME, CONTAINER_NAME_PREFIX, NETWORK_NAME_PREFIX

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
            gateway = '192.168.%d.254' % i
        )
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        networks.append(client.networks.create(name=NETWORK_NAME_PREFIX + str(i), driver='bridge', ipam=ipam_config)) 
        # networks.append(client.networks.create(name=NETWORK_NAME_PREFIX + str(i), driver='bridge')) 
    
    networks[0].connect(container='satellite0', ipv4_address='192.168.1.1')
    networks[0].connect(container='satellite1', ipv4_address='192.168.1.2')
    networks[1].connect(container='satellite1', ipv4_address='192.168.2.1')
    networks[1].connect(container='satellite2', ipv4_address='192.168.2.2')

    # print(nodes[1].exec_run('ifconfig')[1].decode())
    subprocess.run(['docker', 'cp', '/home/sqsq/Desktop/emulator/container_helper_scripts/', 'satellite0:/container_helper_scripts/'])
    res = nodes[0].exec_run('/bin/bash /container_helper_scripts/start_frr.sh', tty=True)[1].decode()
    print(res)

    # print(nodes[0].exec_run('systemctl start frr')[1].decode())
    # print(nodes[0].exec_run('vtysh')[1].decode())
    # print(nodes[0].exec_run('configure terminal')[1].decode())
    # print(nodes[0].exec_run('router ospf')[1].decode())
    # print(nodes[0].exec_run('network 192.168.1.0/24 area 0.0.0.0')[1].decode())

    # print(nodes[1].exec_run('systemctl start frr')[1].decode())
    # print(nodes[1].exec_run('vtysh')[1].decode())
    # print(nodes[1].exec_run('configure terminal')[1].decode())
    # print(nodes[1].exec_run('router ospf')[1].decode())
    # print(nodes[1].exec_run('network 192.168.1.0/24 area 0.0.0.0')[1].decode())
    # print(nodes[1].exec_run('network 192.168.2.0/24 area 0.0.0.0')[1].decode())


    # print(nodes[1].exec_run('exit')[1].decode())
    # print(nodes[1].exec_run('do show ip route')[1].decode())



    try:
        print('containers running, use ctrl+C if you want to stop')
        while True:
            pass
    except KeyboardInterrupt:
        clean(IMAGE_NAME)
        
    pass