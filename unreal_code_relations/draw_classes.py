import math
import os
import random
import time
import json

import networkx as nx
import matplotlib.pyplot as plt

from .py_class import PyClass

G = nx.Graph()
R_G = nx.Graph()
pos = dict()
py_classes = []
fig = None
ax = None

g_edge_color = "#50505030"
g_node_size = []
g_with_labels = False
g_font_size = 8
g_arrowstyle = "->"
g_arrowsize = 10
g_font_color = "#00000080"

g_reference_edges = []

g_xlimits = (-1, 1)
g_ylimits = (-1, 1)

saved_xs = (-1, 1)
saved_ys = (-1, 1)

opt_draw_wire = False
opt_size_mode = 0
opt_label_level = 3

node_type_to_color = {"Object": "#0080FF"
                      , "Enum": "#FF8000"
                      , "Delegate": "#FF0000"
                      , "MultiDelegate": "#FF8000"
                      , "Struct": "#00FF00"}


def group_classes(py_classes, type_and_parentIndex):
    result = dict()
    pname, pid = type_and_parentIndex
    for index, c in enumerate(py_classes):
        if c.name == pname:
            if c.name in result:
                result[c.name].insert(0, c.name)
            else:
                result[c.name] = [c.name]

        if len(c.parents) <= pid:
            continue
        if c.parents[pid] != pname:
            continue

        if len(c.parents) == pid+1:
            if c.name in result:
                result[c.name].insert(0, c.name)
            else:
                result[c.name] = [c.name]
        else:
            local_parent = c.parents[pid+1]
            if local_parent not in result:
                result[local_parent] = []
            result[local_parent].append(c.name)
    return result


def save_pos(file_path, pos):
    content = dict()
    for k, _pos in pos.items():
        content[k] = [_pos[0], _pos[1]]
    with open(file_path, 'w', encoding="UTF-8") as f:
        json.dump(content, f, indent=4, sort_keys=True)
        print(f"save cache pos to {file_path}")

def load_object_positions(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding="UTF-8") as f:
        content = json.load(f)
    return content

def get_catch_file_path(folder):
    return os.path.join(folder, "catched_class_positions.json")


def get_child_count(all_class, class_name):
    return len(all_class[class_name].children)


def redraw_plot(bDrawEdge=True, size_mode = 0):
    global G, pos, g_edge_color, g_node_size, g_with_labels, g_font_size, g_arrowstyle, g_arrowsize, g_font_color
    global fig, ax, g_xlimits, g_ylimits, saved_xs, saved_ys
    global opt_label_level

    plt.cla()

    size_scale = [1, 0.2, 1
                , 1, 1, 1, 1
                 ][size_mode]
    property_name = ["size", "editor_properties_count", "properties_count"
                   , "methods_count", "class_methods_count", "references",  "referenced_by"
                 ][size_mode]
    color = ["#1060a060" #size
            , "#1060a060"    #editor_properties_count
            , "#1060a060"    #properties_count
            , "#1060a060"    #methods_count ok
            , "#1060a060"    #class_methods_count
            , "#1060a060"    #references
            , "#1060a060"    #referenced_by
             ][size_mode]

    print(f"redraw: bDrawEdge {bDrawEdge} size_mode: {size_mode}, property_name: {property_name}")

    canvas_size = ax.get_xlim()[1] - ax.get_xlim()[0]
    g_node_size = [2/canvas_size * size_scale *10 * G.nodes[v][property_name] + 1 if property_name in G.nodes[v] else 1 for v in G.nodes]

    draw_names(property_name, opt_label_level)

    nx.draw(G
            , node_size=g_node_size
            , with_labels=False
            , font_size=8
            # , arrowstyle=g_arrowstyle
            # , arrowsize=g_arrowsize
            , font_color=g_font_color
            , edge_color=g_edge_color
            , node_color = color
            # , node_color = g_node_size
            # , cmap = plt.cm.Blues
            , pos=pos
            )

    plt.draw()

    # draw reference edges
    if bDrawEdge:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=g_reference_edges,
            width=1,
            alpha=0.01,
            edge_color="red",
        )

    ax.set_xlim(saved_xs)
    ax.set_ylim(saved_ys)


def on_key_press(event):
    print(f"on_key_press: {event.key}")
    global G, pos, g_edge_color, g_node_size, g_with_labels, g_font_size, g_arrowstyle, g_arrowsize, g_font_color
    global fig, ax, g_xlimits, g_ylimits, saved_xs, saved_ys
    global opt_draw_wire, opt_size_mode, opt_label_level

    if event.key in [str(v+1) for v in range(8)]: # 1 ~ 9 change label level
        opt_label_level = int(event.key) -1
        redraw_plot(bDrawEdge=opt_draw_wire, size_mode=opt_size_mode)
    elif event.key == "w":  # toggle draw reference edge
        opt_draw_wire = not opt_draw_wire
        redraw_plot(bDrawEdge=opt_draw_wire, size_mode = opt_size_mode)
    elif event.key == "e":   #change draw mode
        opt_size_mode  = (opt_size_mode + 1) % 7
        redraw_plot(bDrawEdge=opt_draw_wire, size_mode = opt_size_mode)
    elif event.key == "d":
        opt_size_mode = (opt_size_mode - 1) % 7
        redraw_plot(bDrawEdge=opt_draw_wire, size_mode=opt_size_mode)
    elif event.key == " ":
        redraw_plot(bDrawEdge=opt_draw_wire, size_mode=opt_size_mode)
    elif event.key == "r":
        X = (g_xlimits[0], g_xlimits[1])
        Y = (g_ylimits[0], g_ylimits[1])
        saved_xs = X
        saved_ys = Y
        print(f"X: {X}, Y: {Y}")


def draw_plot(all_classes, local_folder, iter_count:int):
    # we need prepare all the data, and then draw the plot

    assert type(all_classes) == dict
    global G, pos, g_edge_color, g_node_size, g_with_labels, g_font_size, g_arrowstyle, g_arrowsize, g_font_color
    global fig
    global py_classes
    global g_reference_edges

    # adapt to legacy code
    py_classes = list(all_classes.values())
    name_to_index = {}

    py_classes.sort(key=lambda c: len(c.referenced_by), reverse=True)

    for i, c in enumerate(py_classes):
        name_to_index[c.name] = i

    # group the classes to different categories
    print("Object in all_classes: ", "Object" in all_classes)
    print("StructBase in all_classes: ", "StructBase" in all_classes)
    object_classes = group_classes(py_classes, ("Object", 3)) # ['object', '_WrapperBase', '_ObjectBase', 'Object']
    assert("Object" in object_classes)

    struct_classes = group_classes(py_classes, ("StructBase", 2)) # ['object', '_WrapperBase', 'StructBase', 'RigVMExecuteContext']
    multiDele_classes = group_classes(py_classes, ("MulticastDelegateBase", 2)) #['object', '_WrapperBase', 'MulticastDelegateBase']
    dele_classes = group_classes(py_classes, ("DelegateBase", 2)) #  ['object', '_WrapperBase', 'DelegateBase']
    Enum_classes = group_classes(py_classes, ("EnumBase", 2)) # ['object', '_WrapperBase', 'EnumBase']

    object_classes_flatten = [x for g in object_classes.values() for x in g]
    struct_classes_flatten = [x for g in struct_classes.values() for x in g]

    multiDele_classes_flatten = [x for g in multiDele_classes.values() for x in g]
    dele_classes_flatten = [x for g in dele_classes.values() for x in g]
    enum_classes_flatten = [x for g in Enum_classes.values() for x in g]

    print(f"object_classes: count, total: {len(object_classes_flatten)}:  {len(object_classes)}")# :  {object_classes}")
    print(f"struct_classes: count, total: {len(struct_classes_flatten)}:  {len(struct_classes)}")# :  {struct_classes}")
    print(f"multiDele_classes: count, total: {len(multiDele_classes_flatten)}:  {len(multiDele_classes)}")# :  {multiDele_classes}")
    print(f"dele_classes: count, total: {len(dele_classes_flatten)}:  {len(dele_classes)}")# :  {dele_classes}")
    print(f"Enum_classes: count, total: {len(enum_classes_flatten)}:  {len(Enum_classes)}")# :  {Enum_classes}")

    remain_count = 0
    for i, c in enumerate(py_classes):
        if c.name not in object_classes_flatten \
                and c.name not in struct_classes_flatten \
                and c.name not in multiDele_classes_flatten \
                and c.name not in enum_classes_flatten \
                and c.name not in dele_classes_flatten:
            if remain_count < 20:
                print(f"\tnot grouped: {c.name} {c.parents}")
            elif remain_count == 20:
                print("\ttoo many not grouped...")
            remain_count += 1

    print(f"Remain: {remain_count}")
    assert sum([remain_count, len(object_classes_flatten), len(struct_classes_flatten)
                   , len(multiDele_classes_flatten), len(dele_classes_flatten)
                   , len(enum_classes_flatten)]) == len(py_classes)

    # fill the graph
    G = nx.Graph()

    # calculate the positions and save to cache
    obj_positions = load_object_positions(get_catch_file_path(local_folder))
    if not obj_positions:
        print("no cached pos, start to calculate spring layout")
        node_sizes = []

        node_sizes.append(len(object_classes))

        G.add_nodes_from([(top_object, {"size": len(object_classes[top_object])}) for top_object in object_classes])
        for top_object in object_classes:
            node_sizes.append(len(object_classes[top_object]))

        weighted_edgets = []
        for i, (top_object, children) in enumerate(object_classes.items()):
            weighted_edgets.append(("Object", top_object, 1 / math.pow(len(children), 0.1)))

        G.add_weighted_edges_from(weighted_edgets)

        # First pass, first give the position of the top object
        pos = nx.spring_layout(G)

        G.clear()
        node_sizes = []
        # G.add_nodes_from([("Object")])
        top_objects_nodes = []
        for top_object in object_classes:
            top_objects_nodes.append((top_object, {"size": 1 + get_child_count(all_classes, top_object)}))
            node_sizes.append(len(object_classes[top_object]))

        G.add_nodes_from(top_objects_nodes)

        for parent, children in object_classes.items():
            temp_nodes = []
            for child in children:
                temp_nodes.append((child, {"size": 1 + get_child_count(all_classes, child)}))
            G.add_nodes_from(temp_nodes)

        # edges
        for parent, children in object_classes.items():
            edges = []
            for child in children:
                edges.append((child, all_classes[child].parent, {"size": len(object_classes[top_object])}))
                pos[child] = (pos[parent][0] + random.random() * 0.1, pos[parent][1] + random.random() * 0.1)
            G.add_edges_from(edges)

        print(f"calculate spring layout... node: {len(G.nodes)}, edge: {len(G.edges)}, pos: {len(pos)}")
        if iter_count <= 0 or iter_count > 100:
            iter_count = min(100, max(1, iter_count))
            print("iter_count out of range, clamp to 1 ~ 100")
        # The second pass
        pos = nx.spring_layout(G, pos=pos, iterations=iter_count)
        save_pos(get_catch_file_path(local_folder), pos)

    if True:
        # calculate sizes
        obj_positions = load_object_positions(get_catch_file_path(local_folder))
        node_sizes = []
        top_objects_nodes = []

        for top_object in object_classes:
            c = py_classes[name_to_index[top_object]]
            top_objects_nodes.append((top_object, {"size": 1 + get_child_count(all_classes, top_object)
                , "editor_properties_count": len(c.editor_properties)
                , "properties_count": len(c.properties)
                , "methods_count": len(c.methods)
                , "class_methods_count": len(c.class_methods)
                , "static_methods_count": len(c.static_methods)
                , "referenced_by": c.get_referenced_by_pure()
                , "references":  c.get_references_pure()
                                                   }))
            node_sizes.append(len(object_classes[top_object]))

        G.add_nodes_from(top_objects_nodes)

        for parent, children in object_classes.items():
            temp_nodes = []
            for child in children:
                c = py_classes[name_to_index[child]]
                temp_nodes.append((child, {"size": 1 + get_child_count(all_classes, child)
                    , "editor_properties_count": len(c.editor_properties)
                    , "properties_count": len(c.properties)
                    , "methods_count": len(c.methods)
                    , "class_methods_count": len(c.class_methods)
                    , "static_methods_count": len(c.static_methods)
                    , "referenced_by":  c.get_referenced_by_pure()
                    , "references": c.get_references_pure()
                                           }))
            G.add_nodes_from(temp_nodes)

        # edges
        for parent, children in object_classes.items():
            edges = []
            for child in children:
                edges.append((child, all_classes[child].parent, {"size": len(object_classes[top_object])}))
            G.add_edges_from(edges)

        pos = obj_positions
        print(f"set pos = obj_positions: {len(pos)}")

    print(f"len(node_sizes): {len(node_sizes)} vs len(G.nodes): {len(G.nodes)}")

    edge_colors = []
    for edge in G.edges:
        degree = len(all_classes[edge[0]].children)
        edge_colors.append(degree)

    big_labels = {}
    medium_labels = {}
    for c in py_classes:
        if c.get_type() == "Object":
            child_count = len(c.children)
            if child_count > 30:
                big_labels[c.name] = c.name
            elif child_count > 10:
                medium_labels[c.name] = c.name

    # add reference edges
    for c in py_classes:
        if c.get_type() == "Object":
            for referenced_name, referenced_count in c.references.items():
                if py_classes[name_to_index[referenced_name]].get_type() != "Object":
                    continue
                if referenced_name in c.parents:
                    continue
                for _ in range(referenced_count):
                    g_reference_edges.append((c.name, referenced_name))

    print(f"G.nods: {G.number_of_nodes()}  vs object_classes: {len(object_classes)}, edge: {len(G.edges)}, bigLabel: {len(big_labels)}")

    # do the actual drawing
    redraw_plot(bDrawEdge=opt_draw_wire, size_mode=opt_size_mode)
    plt.show()



def draw_names(property_name, label_level = 0):
    global G, pos, g_edge_color, g_node_size, g_with_labels, g_font_size, g_arrowstyle, g_arrowsize, g_font_color
    global saved_xs, saved_ys
    global py_classes
    assert len(py_classes) > 0, "py_classes is empty"

    print(f"draw_names: property: {property_name} {g_xlimits[1] - g_xlimits[0]}, {g_ylimits[1] - g_ylimits[0]}")

    nodes_in_screen = set()

    label_dict = dict()
    medium_dict = dict()
    small_dict = dict()

    size_pool = []
    size_values = []
    property_pool = []
    property_values = []
    editor_property_pool = []
    editor_property_values = []
    methods_pool = []
    methods_values = []
    class_methods_pool = []
    class_methods_values= []
    referenced_by_pool = []
    referenced_by_values = []
    referenced_pool = []
    referenced_values = []

    value_pool = []
    value_values = []

    added = set()
    for c in py_classes:
        if c.name not in pos:
            continue

        child_count = len(c.children)
        if child_count > 30:
            label_dict[c.name] = c.name
            added.add(c.name)

        size_pool.append(c.name)
        size_values.append(len(c.children))

        editor_property_pool.append(c.name)
        editor_property_values.append(len(c.editor_properties))

        property_pool.append(c.name)
        property_values.append(len(c.properties))

        methods_pool.append(c.name)
        methods_values.append(len(c.methods))

        class_methods_pool.append(c.name)
        class_methods_values.append(len(c.class_methods))

        referenced_by_pool.append(c.name)
        referenced_by_values.append(c.get_referenced_by_pure())

        referenced_pool.append(c.name)
        referenced_values.append(c.get_references_pure())
#
    debug_continue_reason = {"name not in pos": 0, "xs out of range": 0, "ys out of range": 0}
    for c in py_classes:
        if c.name not in pos:
            debug_continue_reason["name not in pos"]  += 1
            continue
        x, y = pos[c.name]
        if x < saved_xs[0] or x > saved_xs[1]:
            debug_continue_reason["xs out of range"] += 1
            continue
        if y < saved_ys[0] or y > saved_ys[1]:
            debug_continue_reason["ys out of range"] += 1
            continue

        nodes_in_screen.add(c.name)
        if property_name == "size":
            value_pool.append(c.name)
            value_values.append(len(c.children))
        elif property_name == "editor_properties_count":
            value_pool.append(c.name)
            value_values.append(len(c.editor_properties))
        elif property_name == "properties_count":
            value_pool.append(c.name)
            value_values.append(len(c.properties))
        elif property_name == "methods_count":
            value_pool.append(c.name)
            value_values.append(len(c.methods))
        elif property_name == "class_methods_count":
            value_pool.append(c.name)
            value_values.append(len(c.class_methods))
        elif property_name == "referenced_by":
            value_pool.append(c.name)
            value_values.append(c.get_referenced_by_pure())
        elif property_name == "references":
            value_pool.append(c.name)
            value_values.append(c.get_references_pure())
#
    size_pool = [x for _, x in sorted(zip(size_values, size_pool), reverse=True)]
    property_pool = [x for _, x in sorted(zip(property_values, property_pool), reverse=True)]
    editor_property_pool = [x for _, x in sorted(zip(editor_property_values, editor_property_pool), reverse=True)]
    methods_pool = [x for _, x in sorted(zip(methods_values, methods_pool), reverse=True)]
    class_methods_pool = [x for _, x in sorted(zip(class_methods_values, class_methods_pool), reverse=True)]
    referenced_by_pool = [x for _, x in sorted(zip(referenced_by_values, referenced_by_pool), reverse=True)]
    referenced_pool = [x for _, x in sorted(zip(referenced_values, referenced_pool), reverse=True)]

    value_pool = [x for _, x in sorted(zip(value_values, value_pool), reverse=True)]

    show_small_count = {3: 5, 4: 15, 5: 40, 6: 100, 7: 300}.get(label_level, 0)


    for n in value_pool:
        if n not in added:
            if len(small_dict) >= show_small_count:
                break
            small_dict[n] = n
            added.add(n)



    if label_level <= 2:
        for i, (pool, reason) in enumerate(zip([size_pool, property_pool, editor_property_pool, methods_pool, class_methods_pool, referenced_by_pool, referenced_pool]
                                            , ["size_pool", "property_pool", "editor_property_pool", "methods_pool", "class_methods_pool", "referenced_by_pool", "referenced_pool"]
                                               )):
            this_added = 0
            for name in pool:
                if name not in added and this_added < 2:
                    if reason != "methods_pool":
                        added.add(name)
                        medium_dict[name] = name
                        # print(f"\tadd {i} top: {name}  because: {reason}")
                    else:
                        # print(f"\tskip {i} top: {name}  because: {reason}")
                        pass

                    this_added += 1



    print(f"nodes in screen: {len(nodes_in_screen)}, py_classes count: {len(py_classes)}")



    # if tiny_dict and label_level > 1:
    #     nx.draw_networkx_labels(G, pos=pos, labels=tiny_dict, font_color="#00000080", font_size=8,
    #                             verticalalignment="top")
    # if small_dict and label_level > 3:
    #     nx.draw_networkx_labels(G, pos=pos, labels=small_dict, font_color="#00000080", font_size=8,verticalalignment="top")
    label_options = {"ec": "#80808040", "fc": "white", "alpha": 0.7}

    small_label_option = {"ec": "#80808040", "fc": "white", "alpha": 0.5}

    if small_dict:
        nx.draw_networkx_labels(G, pos=pos, labels=small_dict, font_color="#202020D0", font_size=10, verticalalignment="top", bbox=small_label_option)

    if medium_dict and label_level > 1:
        nx.draw_networkx_labels(G, pos=pos, labels=medium_dict, font_color="#202020D0", font_weight="bold",  font_size=11, verticalalignment="top", bbox=label_options)
    if label_dict and label_level > 0:
        nx.draw_networkx_labels(G, pos=pos, labels=label_dict, font_color="#000000D0", font_weight="bold", font_size=14,verticalalignment="top", bbox=label_options)

    print(f"Current: {property_name}, label_level: {label_level}, medium_dict: {len(medium_dict)}  small_dict: {len(small_dict)} ")

    labelText = f"{property_name.replace('_', ' ').capitalize()}"
    if labelText == "Size":
        labelText = "Children count"

    plt.suptitle(labelText, x=0.90, y = 0.05, size=11)

    plt.draw()
    # nx.draw_networkx_labels(G, pos=pos, labels=big_labels, font_color="#000000D0", font_size=12, verticalalignment="top")


def on_xlimts_change(event_ax):
    pass

def on_ylimts_change(event_ax):
    pass

def on_mouse_release(event):
    print(f"on_mouse_release: {event}")
    global saved_xs, saved_ys, pos
    global ax
    saved_xs = ax.get_xlim()
    saved_ys = ax.get_ylim()

    mouse_x, mouse_y = event.xdata, event.ydata


    near_nodes = []
    near_nodes_distance= []

    for name, coord in pos.items():
        delta_x = abs(coord[0] - mouse_x)
        if delta_x > 0.01:
            continue
        delta_y = abs(coord[1] - mouse_y)
        if delta_y > 0.01:
            continue
        near_nodes.append(name)
        near_nodes_distance.append(math.sqrt(delta_x*delta_x + delta_y*delta_y))

    near_nodes = [x for _, x in sorted(zip(near_nodes_distance, near_nodes), reverse=True)]
    near_labels = {x: x for i, x in enumerate(near_nodes) if i < 1}

    if near_nodes:
        small_label_option = {"ec": "#00000000", "fc": "white", "alpha": 0.4}
        nx.draw_networkx_labels(G, pos=pos, labels=near_labels, font_color="#202020D0", font_size=7, verticalalignment="top",
                                # bbox=small_label_option
                                )

    print(f"\ton_mouse_release: {saved_xs} {saved_ys}, {(mouse_x, mouse_y)}")
    print(f"near nodes: {len(near_nodes)} :{near_nodes}")


def draw(py_classes, local_folder, delete_cache=True, iter_count= 8):
    if delete_cache:
        saved_file_folder = get_catch_file_path(local_folder)
        if os.path.exists(saved_file_folder):
            os.remove(saved_file_folder)
            print(f"delete cache file: {saved_file_folder}")

    print("Draw")
    global ax, fig
    fig = plt.figure(figsize=(12, 7), dpi=96)
    fig.canvas.mpl_connect('key_press_event', on_key_press)

    ax = fig.add_axes([0.05, 0.05, 1, 1])
    ax.grid(True)

    fig.canvas.mpl_connect('button_release_event', on_mouse_release)

    draw_plot(py_classes, local_folder=local_folder, iter_count=iter_count)


