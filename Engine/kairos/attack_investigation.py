import os

from graphviz import Digraph
import networkx as nx
#?import datetime
import community.community_louvain as community_louvain
from tqdm import tqdm

from .config import *
from .kairos_utils import *
ATTACK_LIST = [
    '/home/postgres/kairos/artifact/graph_4_6/2018-04-06 11:18:26.126177915~2018-04-06 11:33:35.116170745.txt',
]

#! 打桩
abnormal_output = open("./anormaly.txt","w",encoding="utf-8")
dangerous_output = open("./dangerous.txt","w",encoding="utf-8")
# Some common path abstraction for visualization

def replace_path_name(path_name):
    for i in REPLACE_DICT:
        if i in path_name:
            return REPLACE_DICT[i]
    return path_name

# Users should manually put the detected anomalous time windows here

original_edges_count = 0
graphs = []
gg = nx.DiGraph()
count = 0
for path in tqdm(ATTACK_LIST):
    if ".txt" in path:
        line_count = 0
        node_set = set()
        tempg = nx.DiGraph()
        f = open(path, "r")
        edge_list = []
        for line in f:
            count += 1
            l = line.strip()
            jdata = eval(l)
            edge_list.append(jdata)

        edge_list = sorted(edge_list, key=lambda x: x['loss'], reverse=True)
        original_edges_count += len(edge_list)

        loss_list = []
        for i in edge_list:
            loss_list.append(i['loss'])
        loss_mean = mean(loss_list)
        loss_std = std(loss_list)
        print(loss_mean)
        print(loss_std)
        thr = loss_mean + 1.5 * loss_std
        print("thr:", thr)
        for e in edge_list:
            if e['loss'] > thr:
                tempg.add_edge(str(hashgen(replace_path_name(e['srcmsg']))),
                               str(hashgen(replace_path_name(e['dstmsg']))))
                gg.add_edge(str(hashgen(replace_path_name(e['srcmsg']))), str(hashgen(replace_path_name(e['dstmsg']))),
                            loss=e['loss'], srcmsg=e['srcmsg'], dstmsg=e['dstmsg'], edge_type=e['edge_type'],
                            time=e['time'])


partition = community_louvain.best_partition(gg.to_undirected())

# Generate the candidate subgraphs based on community discovery results
communities = {}
max_partition = 0
for i in partition:
    if partition[i] > max_partition:
        max_partition = partition[i]
for i in range(max_partition + 1):
    communities[i] = nx.DiGraph()
for e in gg.edges:
    communities[partition[e[0]]].add_edge(e[0], e[1])
    communities[partition[e[1]]].add_edge(e[0], e[1])


# Define the attack nodes. They are **only be used to plot the colors of attack nodes and edges**.
# They won't change the detection results.
def attack_edge_flag(msg):
    attack_nodes = ATTACK_NODES[DETECTION_LEVEL]
    flag = False
    for i in attack_nodes:
        if i in msg:
            flag = True
    return flag


# Plot and render candidate subgraph
os.system(f"mkdir -p {ARTIFACT_DIR}/graph_visual/")

graph_index = 0

for c in communities:
    dot = Digraph(name="MyPicture", comment="the test", format="pdf")
    dot.graph_attr['rankdir'] = 'LR'

    for e in communities[c].edges:
        try:
            temp_edge = gg.edges[e]
            srcnode = e['srcnode']
            dstnode = e['dstnode']
        except:
            pass

        if True:
            # source node
            if "'subject': '" in temp_edge['srcmsg']:
                src_shape = 'box'
            elif "'file': '" in temp_edge['srcmsg']:
                src_shape = 'oval'
            elif "'netflow': '" in temp_edge['srcmsg']:
                src_shape = 'diamond'
            if attack_edge_flag(temp_edge['srcmsg']):
                src_node_color = 'red'
            else:
                src_node_color = 'blue'
            dot.node(name=str(hashgen(replace_path_name(temp_edge['srcmsg']))), label=str(
                replace_path_name(temp_edge['srcmsg']) + str(
                    partition[str(hashgen(replace_path_name(temp_edge['srcmsg'])))])), color=src_node_color,
                     shape=src_shape)

            # destination node
            if "'subject': '" in temp_edge['dstmsg']:
                dst_shape = 'box'
            elif "'file': '" in temp_edge['dstmsg']:
                dst_shape = 'oval'
            elif "'netflow': '" in temp_edge['dstmsg']:
                dst_shape = 'diamond'
            if attack_edge_flag(temp_edge['dstmsg']):
                dst_node_color = 'red'
            else:
                dst_node_color = 'blue'
            dot.node(name=str(hashgen(replace_path_name(temp_edge['dstmsg']))), label=str(
                replace_path_name(temp_edge['dstmsg']) + str(
                    partition[str(hashgen(replace_path_name(temp_edge['dstmsg'])))])), color=dst_node_color,
                     shape=dst_shape)

            if attack_edge_flag(temp_edge['srcmsg']) and attack_edge_flag(temp_edge['dstmsg']):
                dangerous_output.write(f"{temp_edge['srcmsg']} --{temp_edge['edge_type']}--{temp_edge['dstmsg']}/{temp_edge['time']}\n")
                edge_color = 'red'
            else:
                abnormal_output.write(f"{temp_edge['srcmsg']} --{temp_edge['edge_type']}--{temp_edge['dstmsg']}/{ns_time_to_datetime(temp_edge['time'])}\n")
                edge_color = 'blue'
            dot.edge(str(hashgen(replace_path_name(temp_edge['srcmsg']))),
                     str(hashgen(replace_path_name(temp_edge['dstmsg']))), label=temp_edge['edge_type'],
                     color=edge_color)

    dot.render(f'{ARTIFACT_DIR}/graph_visual/subgraph_' + str(graph_index), view=False)
    graph_index += 1
