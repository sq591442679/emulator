import docker
import common
from threading import Thread


def stopAndRemoveContainer(container):
    container.stop()
    container.remove()
    

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
    
    for network in client.networks.list():
        if common.NETWORK_NAME_PREFIX in network.name:
            network.remove()

    print('all containers and networks are stopped and removed')

if __name__ == '__main__':
    clean(common.IMAGE_NAME)