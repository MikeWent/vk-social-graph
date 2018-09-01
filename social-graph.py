#!/usr/bin/env python

import argparse
import json
from os.path import exists as file_exists
from random import randint
from time import sleep
from os import makedirs

import matplotlib
# don't use X11 as backend on headless machines
# (should be executed before pyplot)
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

import vk_api

args = argparse.ArgumentParser()
args.add_argument("-t", "--target", help="target root user, default is current user id", metavar="ID")
args.add_argument("-s", "--size", help="graph width and height, default is 100 80", metavar="N", type=int, nargs=2, default=(100, 80))
args.add_argument("-f", "--font-size", help="font size of node labels (names), default is 8", type=int, default=8)
args.add_argument("-o", "--output", help="output filename **without extension** (.svg or .png), default is 'social-graph-{root_user_id}'", metavar="FILENAME")
args.add_argument("-p", "--png", help="generate png file too (they are very large)", action="store_true")
options = args.parse_args()


def delay():
    """Sleep 0.3-0.4 seconds"""
    try:
        sleep(randint(3, 4) / 10)
    except KeyboardInterrupt:
        exit()


def filter_user_data(user_data):
    """Get a dict of filtered information
    
    Arguments:
        user_data {dict} -- raw user info got from vk.users.get
    """
    return {"id": user_data["id"],
            "name": user_data["first_name"] + "\n" + user_data["last_name"],
            "sex": user_data["sex"]}


def get_user_info(user_id=None):
    """Get user info by user id
    
    Arguments:
        user_id {int} -- target user id or a link (default: None)
    
    Returns:
        dict -- user id, name and sex (1 - female, 2 - male)
    """

    try:
        user_data =  vk.users.get(user_ids=user_id, fields="sex")[0]
    except vk_api.VkApiError:
        return None
    return filter_user_data(user_data)

def get_user_friends(user_id=None):
    """Get a list of user friends
    
    Arguments:
        user_id {int} -- target user id
    
    Returns:
        list -- a list of user ids
    """
    try:
        friends = vk.friends.get(user_id=user_id, order="hints", fields="sex").get("items", None)
    except vk_api.VkApiError:
        return []
    list_with_filtered_info = []
    for user_data in friends:
        list_with_filtered_info.append(filter_user_data(user_data))
    return list_with_filtered_info


def tree_lookup(user_id):
    global friendship_tree
    for user in friendship_tree:
        if user["id"] == user_id:
            return user
        for friend in user["friends"]:
            if friend["id"] == user_id:
                return friend


success_auth = False
while not success_auth:
    try:
        with open("access_token.txt", "r") as f:
            access_token = f.read().rstrip()
        vk_session = vk_api.VkApi(token=access_token)
        try:
            vk = vk_session.get_api()
            if vk.users.get():
                success_auth = True
                break
        except vk_api.VkApiError:
            pass
    except FileNotFoundError:
        pass
    import auth
    print("---")

if options.target:
    root_user_link = options.target
else:
    root_user_link = None
root_user_data = get_user_info(root_user_link)
root_user_id = root_user_data["id"]

cache_dir = "cache/"
makedirs(cache_dir, exist_ok=True)
friendship_tree_path = cache_dir+"tree-{}.json".format(root_user_id)
networkx_graph_path = cache_dir+"graph-{}.gpickle".format(root_user_id)

if file_exists(friendship_tree_path):
    with open(friendship_tree_path, "r") as f:
        friendship_tree = json.load(f)
    print("Friendship tree for user {} loaded from cache".format(root_user_id))
else:
    friendship_tree = []
    root_user_friends = get_user_friends(root_user_id)
    for n, friend in enumerate(root_user_friends, start=1):
        print("Fetching friends and friends of friends: {}/{}...".format(n, len(root_user_friends)), end="\r")
        friends_of_friend = get_user_friends(friend["id"])
        friend.update({"friends": friends_of_friend})
        friendship_tree.append(friend)
        delay()
    print()
    with open(friendship_tree_path, "w") as f:
        json.dump(friendship_tree, f, indent=2)
    print("Friendship tree for user {} saved to {}...".format(root_user_id, friendship_tree_path))

if file_exists(networkx_graph_path):
    G = nx.readwrite.read_gpickle(networkx_graph_path)
    print("Graph data for user {} loaded from cache".format(root_user_id))
else:
    print("Building base graph...")
    G = nx.Graph()
    G.add_node(root_user_id)
    for friend in friendship_tree:
        G.add_node(friend["id"])
        # connect root user to his primary friends
        G.add_edge(root_user_id, friend["id"])

    for n, primary_friend in enumerate(friendship_tree, start=1):
        print("Processing graph: {}/{}...".format(n, len(friendship_tree)), end="\r")
        for user_x in primary_friend["friends"]:
            for _primary_friend_ in friendship_tree:
                if user_x in _primary_friend_["friends"] and _primary_friend_ != primary_friend:
                    if not user_x in G:
                        G.add_node(user_x["id"])
                    G.add_edge(user_x["id"], _primary_friend_["id"])
    print()
    nx.readwrite.write_gpickle(G, networkx_graph_path)
    print("Graph data saved to {}".format(networkx_graph_path))

print("Visualizing the graph...")
def choose_color(node):
    if node == root_user_id:
        return "green"
    sex = tree_lookup(node)["sex"]
    if sex == 1:
        # female
        return "red"
    elif sex == 2:
        # male
        return "skyblue"
    else:
        # unknown
        return "black"

node_sizes = [len(list(nx.all_neighbors(G, node))) * 15 for node in G.nodes()]
node_linewidths = [len(list(nx.all_neighbors(G, node))) * 2 for node in G.nodes()]
node_labels = {node: tree_lookup(node)["name"] for node in G.nodes()}
node_colors = [choose_color(node) for node in G.nodes()]
edge_colors = ["#%06X" % randint(0,256**3-1) for _ in range(len(G.edges()))]

plt.figure(figsize=options.size)
plt.axis("off")
plt.margins(0.01)
pos = nx.spring_layout(G)

node_options = {
    "with_labels": True,
    "node_size": node_sizes,
    "alpha": 0.3,
    "node_color": node_colors
}
nx.draw_networkx_nodes(G, pos, **node_options)

edge_options = {
    "edge_color": edge_colors,
    "edge_vmin": 1.0,
    "edge_vmax": 999.0,
    "alpha": 0.5,
    "width": 0.5
}
nx.draw_networkx_edges(G, pos, **edge_options)

label_options = {
    "labels": node_labels,
    "font_size": options.font_size,
    "font_color": "black",
    "alpha": 0.8
}
nx.draw_networkx_labels(G, pos, **label_options)

if options.output:
    svg_filename = options.output+".svg"
    png_filename = options.output+".png"
else:
    img_dir = "img/"
    makedirs(img_dir, exist_ok=True)
    base_name = img_dir+"social-graph-{}".format(root_user_id)
    svg_filename = base_name+".svg"
    png_filename = base_name+".png"

export_params = {
    "bbox_inches": "tight",
    "pad_inches": 0
}
print("Creating SVG image...")
plt.savefig(svg_filename, **export_params)
print("SVG image saved to {}".format(svg_filename))
if options.png:
    print("Creating PNG image...")
    plt.savefig(png_filename, **export_params)
    print("PNG image saved {}".format(png_filename))
