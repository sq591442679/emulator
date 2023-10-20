import random
import time
import multiprocessing
import sys
import math
import subprocess
import typing
import os


LINK_DOWN_DURATION = 5
SIMULATION_DURATION = 100
SIMULATION_END_TIME = SIMULATION_DURATION


def generate_event_for_interface(container_name:str, interface_name: str, link_failure_rate: float, seed=None):

    if abs(link_failure_rate - 0)< 1e-6:
        return

    interface_failure_rate = 1 - math.sqrt(1 - link_failure_rate)
    poisson_lambda = interface_failure_rate / (LINK_DOWN_DURATION * (1 - interface_failure_rate))

    if seed != None:
        random.seed(seed)

    start_time = time.time()
    current_sim_time = time.time() - start_time

    while current_sim_time <= SIMULATION_END_TIME:
        sim_time_interval = random.expovariate(poisson_lambda)

        if current_sim_time + sim_time_interval >= SIMULATION_END_TIME:  # if there aren't any failures during this simulation, then break
            # current_sim_time = SIMULATION_END_TIME + LINK_DOWN_DURATION
            break
        
        time.sleep(sim_time_interval)

        current_sim_time = time.time() - start_time
        if current_sim_time >= SIMULATION_END_TIME:
            break

        print('{"sim_time": %.3f, "intf": "%s.%s", "type": "down"}' % (current_sim_time, container_name, interface_name), flush=True)
        os.system("ifconfig %s down" % interface_name)
        # subprocess.run(["ifconfig", interface_name, "down"])

        current_sim_time = time.time() - start_time
        if current_sim_time >= SIMULATION_END_TIME:
            break

        time.sleep(LINK_DOWN_DURATION)

        current_sim_time = time.time() - start_time
        if current_sim_time >= SIMULATION_END_TIME:
            break
        
        if current_sim_time <= SIMULATION_END_TIME:
            print('{"sim_time": %.3f, "intf": "%s.%s", "type": "up"}' % (current_sim_time, container_name, interface_name), flush=True)
            os.system("ifconfig %s up" % interface_name)
            # subprocess.run(["ifconfig", interface_name, "up"])

        current_sim_time = time.time() - start_time

    # print('{"at": %.3f, "intf": "%s.%s", "type": "generation done"}' % (current_sim_time, container_name, interface_name), flush=True)


"""
argv[1]: link failure rate
argv[2]: container name
argv[3]: whether can shut eth1 down
argv[4]: random seed
"""
if __name__ == '__main__':
    start_time = time.time()
    link_failure_rate = float(sys.argv[1])
    container_name = sys.argv[2]
    can_shut_eth1_down = bool(sys.argv[3])

    process_list: typing.List[multiprocessing.Process] = []

    if len(sys.argv) == 5:
        seed = int(sys.argv[4])
    else:
        seed = random.randint(1, 0x3f3f3f3f)

    random.seed(seed)
    process_seed_list = []
    for i in range(1, 5):
        process_seed_list.append(random.randint(1, 0x3f3f3f3f))

    interface_name_list = []
    if can_shut_eth1_down:
        interface_name_list = ['eth%d' % i for i in range(1, 5)]
    else:
        interface_name_list = ['eth%d' % i for i in range(2, 5)]

    for i in range(len(interface_name_list)):
        process = multiprocessing.Process(target=generate_event_for_interface, 
                                          args=(container_name, interface_name_list[i], link_failure_rate, process_seed_list[i]))
        process_list.append(process)

    for process in process_list:
        process.start()

    for process in process_list:
        process.join()

    pass