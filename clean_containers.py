import docker
import common
from threading import Thread


def stopAndRemoveContainer(container):
    container.stop()
    container.remove()


def removeNetwork(network):
    network.remove()
    

def clean(image_name:str):
    print('')
    print('please wait for container stopping...')

    client = docker.from_env()

    threads = []

    for container in client.containers.list():
        for tag in container.image.tags:
            if image_name in tag:
                thread = Thread(target=stopAndRemoveContainer, args=(container, ))
                thread.start()
                threads.append(thread)

    for thread in threads:
        thread.join()
    
    threads = []

    for network in client.networks.list():
        if common.NETWORK_NAME_PREFIX in network.name:
            thread = Thread(target=removeNetwork, args=(network, ))
            thread.start()
            threads.append(thread)
            
    for thread in threads:
        thread.join()

    print('all containers and networks are stopped and removed')

if __name__ == '__main__':
    image_name = 'lightweight:n_0'
    clean(image_name)