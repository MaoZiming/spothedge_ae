from typing import List

import numpy as np
import simpy

from policies import workload as workload_lib
from utils import config

NUM_CLIENTS = 3


class CustomStore(simpy.Store):
    def put_at_front(self, item):
        self.items.insert(0, item)


class NodesList:
    def __init__(self) -> None:
        self.nodes: List[Node] = []
        pass


class Node:
    def __init__(self, env, name, workload):
        self.env = env
        self.name = name
        self.queue = CustomStore(env)
        self.workload = workload
        self.busy = False

    def serve_request(self, request, serving_times):
        self.busy = True
        start_time = request[1]  # Arrival time
        if self.env.now - start_time > self.workload.timeout:
            self.busy = False
            serving_times.append(self.workload.timeout)
            return False
        yield self.env.timeout(np.random.exponential(1 / self.workload.service_rate))
        end_time = self.env.now
        serving_times.append(end_time - start_time)
        self.busy = False
        return True


# def _put_request_in_least_loaded_node(nodes, request):
#     # Find the node with the shortest queue.
#     # this parts departs from the e2e evaluation.
#     node_length_list = [len(node.queue.items) for node in nodes.nodes]
#     node_idx = np.argmin(node_length_list)
#     node = nodes.nodes[node_idx]

#     node.queue.put(request)


def client(env, nodes, workload, serving_times):
    i = 0
    node_idx = 0
    while True:
        yield env.timeout(workload.get_next_interarrival_time(i))
        i += 1
        request = (f"Request-{i + 1}", env.now)  # Include arrival time

        # If all nodes are preempted.
        if len(nodes.nodes) == 0:
            serving_times.append(workload.timeout)
            continue

        # _put_request_in_least_loaded_node(nodes, request)
        node = nodes.nodes[node_idx % len(nodes.nodes)]
        node.queue.put(request)
        node_idx += 1


def server(env, nodes, serving_times):
    while True:
        for node in nodes.nodes:
            # Serve requests if node is not busy and request in queue.
            if not node.busy and len(node.queue.items) > 0:
                request = node.queue.get().value
                env.process(node.serve_request(request, serving_times))
        yield env.timeout(0.01)


def adjust_nodes(env, nodes, node_counts, workload, serving_times):
    for _, count in enumerate(node_counts):
        if len(nodes.nodes) < count:
            while len(nodes.nodes) < count:
                node = Node(
                    env,
                    f"Node-{len(nodes.nodes) + 1}",
                    workload=workload,
                )
                nodes.nodes.append(node)
        elif count < len(nodes.nodes):
            excess_nodes = nodes.nodes[count:]
            nodes.nodes = nodes.nodes[:count]
            for node in excess_nodes:
                # redistribute_requests(nodes, node, serving_times, workload)

                # Timeout all the nodes.
                while len(node.queue.items) > 0:
                    node.queue.get().value
                    serving_times.append(workload.timeout)

        assert len(nodes.nodes) == count
        yield env.timeout(config.time_tick_in_seconds)


# def redistribute_requests(nodes, dropped_node, serving_times, workload):
#     while len(dropped_node.queue.items) > 0:
#         request = dropped_node.queue.get().value
#         if len(nodes.nodes) == 0:
#             serving_times.append(workload.timeout)
#             continue

#         _put_request_in_least_loaded_node(nodes, request)


# Shift the time by i.
def simulate_latency(node_counts, workload: workload_lib.Workload, i=0):
    env = simpy.Environment()
    nodes: NodesList = NodesList()
    serving_times: List[float] = list()
    workloads = []
    for i in range(NUM_CLIENTS):
        workload = type(workload)(seed=i, use_simulator=True)
        env.process(
            client(
                env,
                nodes,
                workload=workload,
                serving_times=serving_times,
            )
        )
        workloads.append(workload)

    env.process(server(env, nodes, serving_times))
    env.process(
        adjust_nodes(
            env,
            nodes,
            node_counts=node_counts,
            workload=workloads[0],
            serving_times=serving_times,
        )
    )

    print(
        f"Running simulation for {len(node_counts)} time periods, {node_counts[:50]}, average: {sum(node_counts) / len(node_counts)}"
    )
    # print(len(node_counts) * config.time_tick_in_seconds + 1)
    env.run(until=len(node_counts) * config.time_tick_in_seconds + 1)
    assert len(serving_times) >= 1, node_counts
    average_latency = np.average(serving_times)
    p99_latency = np.percentile(serving_times, 99)
    p90_latency = np.percentile(serving_times, 90)
    p50_latency = np.percentile(serving_times, 50)
    p999_latency = np.percentile(serving_times, 99.9)

    print(
        f"average_latency: {average_latency}, p50_latency: {p50_latency:.2f}, p90_latency: {p90_latency:.2f}, p99_latency: {p99_latency:.2f}, P999: {p999_latency:.2f}"
    )
    return (
        p50_latency,
        p90_latency,
        p99_latency,
        p999_latency,
        serving_times[0 : len(serving_times) : 10],
    )
