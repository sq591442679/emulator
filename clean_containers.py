import docker
import variables


def clean(image_name:str):
    print('')
    print('please wait for container stopping...')

    client = docker.from_env()

    for container in client.containers.list():
        for tag in container.image.tags:
            if image_name in tag:
                container.stop()
                container.remove()
    
    for network in client.networks.list():
        if variables.NETWORK_NAME_PREFIX in network.name:
            network.remove()

    print('all containers and networks are stopped and removed')

if __name__ == '__main__':
    clean(variables.IMAGE_NAME)