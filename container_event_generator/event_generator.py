import random
import time
import multiprocessing
import sys
import math
import subprocess
import typing


WARMUP_PERIOD = 20  # unit: s
LINK_DOWN_DURATION = 5
SIMULATION_DURATION = 100
SIMULATION_END_TIME = WARMUP_PERIOD + SIMULATION_DURATION


def generate_event_for_interface(container_name:str, interface_name: str, link_failure_rate: float, seed=None):
    interface_failure_rate = 1 - math.sqrt(1 - link_failure_rate)
    poisson_lambda = interface_failure_rate / (LINK_DOWN_DURATION * (1 - interface_failure_rate))

    if seed != None:
        random.seed(seed)

    start_time = time.time()
    current_sim_time = time.time() - start_time

    while current_sim_time <= SIMULATION_END_TIME:
        sim_time_interval = random.expovariate(poisson_lambda)
        time.sleep(sim_time_interval)

        current_sim_time = time.time() - start_time
        print("at %.3f, %s.%s goes down" % (current_sim_time, container_name, interface_name), flush=True)
        subprocess.run(["ifconfig", interface_name, "down"])

        time.sleep(LINK_DOWN_DURATION)

        current_sim_time = time.time() - start_time
        print("at %.3f, %s.%s goes up" % (current_sim_time, container_name, interface_name), flush=True)
        subprocess.run(["ifconfig", interface_name, "up"])

        current_sim_time = time.time() - start_time
    pass


"""
argv[1]: link failure rate
argv[2]: container name
argv[3]: random seed
"""
if __name__ == '__main__':
    link_failure_rate = float(sys.argv[1])
    container_name = sys.argv[2]

    time.sleep(WARMUP_PERIOD)

    process_list: typing.List[multiprocessing.Process] = []

    if len(sys.argv) == 4:
        seed = int(sys.argv[3])
    else:
        seed = random.randint(1, 0x3f3f3f3f)

    random.seed(seed)
    process_seed_list = []
    for i in range(1, 5):
        process_seed_list.append(random.randint(1, 0x3f3f3f3f))

    interface_name_list = ['eth%d' % i for i in range(1, 5)]
    for i in range(len(interface_name_list)):
        process = multiprocessing.Process(target=generate_event_for_interface, 
                                          args=(container_name, interface_name_list[i], link_failure_rate, process_seed_list[i]))
        process_list.append(process)
        process.start()

    for process in process_list:
        process.join()

    pass