"""
This module is the only one capable of referencing the map G
and thus contains methods for updating car position and finding path to car destination;
also contains methods for locating cars and intersections in the front_view
and calculating the curvature of the bend in the road for speed adjustments
"""
import models
import networkx as nx
import numpy as np
import osmnx as ox


G = ox.load_graphml('piedmont.graphml')
# G = ox.load_graphml('sanfrancisco.graphml')
# G = ox.load_graphml('lowermanhattan.graphml')
G = ox.project_graph(G)


class FrontView:
    def __init__(self, car, look_ahead_nodes=3):
        """
        take a car Series and determines the obstacles it faces in its frontal view

        :param              car: Series row of the main dataframe
        :param look_ahead_nodes: int
        """
        self.look_ahead_nodes = look_ahead_nodes
        self.car = car
        self.position = car['x'], car['y']
        self.view = self.determine_view()
        self.angles = models.get_angles(self.view)

    def determine_view(self):
        """
        this method handles the exception where the path is shorter than look_ahead_nodes

        :return view: list or bool: list of nodes immediately ahead of the car or False if end of route
        """
        if self.car['xpath'] and self.car['ypath']:
            x, y = self.car['xpath'][:self.look_ahead_nodes], self.car['ypath'][:self.look_ahead_nodes]
            return [(x[i], y[i]) for i in range(len(x))]
        else:
            return False

    def distance_to_car(self, cars):
        """
        dispatches a car Series into another nav function and retrieves the distance to a car obstacle if there is one

        :param      cars: Dataframe of cars
        :return distance:
        """
        return car_obstacles(self, cars)

    def distance_to_light(self, lights):
        """
        dispatches a car Series into another nav function and retrieves the distance to a red light if there is one

        :param    lights: Dataframe of lights
        :return distance:
        """
        return light_obstacles(self, lights)

    def distance_to_node(self):
        """
        Determines the distance to the most immediate node

        :return distance: double
        """
        next_node = np.array(self.upcoming_node_position())
        distance_vector = next_node - self.position
        distance = models.magnitude(distance_vector)
        return distance

    def upcoming_node_position(self):
        """
        Determines the coordinates of the next node in view

        :return view: tuple: returns upcoming node coords in the path
        """
        if self.view:
            if self.crossed_node_event():
                return self.view[1]
            else:
                return self.view[0]
        else:
            # end of route
            return get_position_of_node(self.car['destination'])

    def crossed_node_event(self):
        """
        Determines if the car has crossed a node, and advises simulation to change
        its velocity vector accordingly

        :return bool: True if the car is passing a node, False otherwise
        """
        car_near_xnode = np.isclose(self.view[0][0], self.car['x'], rtol=1.0e-6)
        car_near_ynode = np.isclose(self.view[0][1], self.car['y'], rtol=1.0e-6)

        if car_near_xnode and car_near_ynode:
            return True
        else:
            return False


def car_obstacles(frontview, cars):
    """

    Parameters
    __________
    :param frontview:    object: FrontView object
    :param      cars: dataframe:

    Returns
    _______
    :return distance: list: double or False (returns False if no car obstacle found)
    """
    # TODO: This method is slow because, for n cars, O(n^2) complexity occurs when it is used each times-step.
    # TODO: Switch to smart sorting.
    space = models.upcoming_linspace(frontview)
    x_space = space[0]
    y_space = space[1]

    x_obstacle_position, y_obstacle_position = [], []
    for x_obstacle, y_obstacle in zip(cars['x'], cars['y']):
        car_within_xlinspace = np.isclose(x_space, x_obstacle, rtol=1.0e-6).any()
        car_within_ylinspace = np.isclose(y_space, y_obstacle, rtol=1.0e-6).any()

        if car_within_xlinspace and car_within_ylinspace:
            x_obstacle_position.append(x_obstacle)
            y_obstacle_position.append(y_obstacle)

    if x_obstacle_position and y_obstacle_position:
        first_x, first_y = x_obstacle_position[0], y_obstacle_position[0]
        vector = (first_x - frontview.car['x'], first_y - frontview.car['y'])
        distance = models.magnitude(vector)
        return distance
    else:
        return False


def light_obstacles(frontview, lights):
    """
    Determines the distance to red traffic lights. If light is green, returns False

    Parameters
    __________
    :param  frontview:    object: FrontView object
    :param     lights: dataframe:

    Returns
    _______
    :return distance: list: double for False (returns False if no red light is found)
    """
    # TODO: This method is slow because, for n lights, O(n^2) complexity occurs when it is used each times-step.
    # TODO: Switch to smart sorting.
    space = models.upcoming_linspace(frontview)
    x_space = space[0]
    y_space = space[1]

    light_index = []
    for light in lights.iterrows():
        light_within_xlinspace = np.isclose(x_space, light[1]['x'], rtol=1.0e-6).any()
        light_within_ylinspace = np.isclose(y_space, light[1]['y'], rtol=1.0e-6).any()

        if light_within_xlinspace and light_within_ylinspace:
            light_index.append(light[0])

    if light_index:
        light = lights.loc[light_index[0]]
        car_vector = [light['x'] - frontview.car['x'], light['y'] - frontview.car['y']]
        face_values = light['go-values']
        face_vectors = [(light['out-xvectors'][i], light['out-yvectors'][i]) for i in range(light['degree'])]

        for value, vector in zip(face_values, face_vectors):
            if not value and models.determine_parralel_vectors(car_vector, vector):
                distance = models.magnitude(car_vector)
                return distance
            else:
                continue

        # if the above for loop finished without returning a distance, then return False
        # note that this would happen only in the case where there is a bug (i.e. no parallel vector was found)
        return False

    else:
        return False


def determine_pedigree(node_id):
    """
     each traffic light has a list of vectors, pointing in the direction of the road a light color should influence

     :param  node_id:    int
     :return vectors:   list: list of vectors pointing from the intersection to the nearest point on the out roads
     """
    position = get_position_of_node(node_id)

    left_edges = []
    right_edges = []
    for edge in G.edges():
        if edge[0] == node_id:
            left_edges.append(edge)
        if edge[1] == node_id:
            right_edges.append(edge)

    for left in left_edges:
        for i, right in enumerate(right_edges):
            if (left[1] == right[0]) and (right[1] == left[0]):
                right_edges.pop(i)

    intersection_edges = left_edges + right_edges

    out_nodes = []
    for edge in intersection_edges:
        if edge[0] == node_id:
            out_nodes.append(edge[1])
        else:
            out_nodes.append(edge[0])

    vectors = []
    for node in out_nodes:
        try:
            point = lines_to_node(node_id, node)[0][1]
        except IndexError:
            continue
        vectors.append((point[0] - position[0], point[1] - position[1]))

    return vectors


def find_culdesacs():
    """
    culdesacs are nodes with only one edge connection and which are not on the boundary of the OpenStreetMap

    :return culdesacs: list of node IDs
    """
    culdesacs = [key for key, value in G.graph['streets_per_node'].items() if value == 1]
    return culdesacs


def find_traffic_lights():
    """
    traffic lights are nodes in the graph which have degree > 3

    :return light_intersections: a list of node IDs suitable for traffic lights
    """
    prescale = 4
    light_intersections = []
    for i, node in enumerate(G.degree()):
        if (node[1] > 3) and not (i % prescale):
            light_intersections.append(node)

    return light_intersections


def find_nodes(n):
    """
    returns n node IDs from the networkx graph

    :param      n: int
    :return nodes: list
    """
    nodes = []
    for node in G.nodes():
        nodes.append(node)
    return nodes[:n]


def get_position_of_node(node):
    """
    Get latitude and longitude given node ID

    :param node:      graphml node ID
    :return position: array:    [latitude, longitude]
    """
    # note that the x and y coordinates of the G.nodes are flipped
    # this is possibly an issue with the omnx G.load_graphml method
    # a correction is to make the position tuple be (y, x) as below
    position = np.array([G.nodes[node]['x'], G.nodes[node]['y']])
    return position


def get_init_path(origin, destination):
    """
    compiles a list of tuples which represents a route

    Parameters
    __________
    :param      origin: int:    node ID
    :param destination: int:    node ID

    Returns
    _______
    :return path: list where each entry is a tuple of tuples
    """
    lines = shortest_path_lines_nx(origin, destination)
    path = models.path_decompiler(lines)
    return path


def lines_to_node(origin, destination):
    """

    :param origin:
    :param destination:
    :return:
    """

    route = nx.shortest_path(G, origin, destination, weight='length')

    # find the route lines
    edge_nodes = list(zip(route[:-1], route[1:]))
    lines = []
    for u, v in edge_nodes:
        # if there are parallel edges, select the shortest in length
        data = min(G.get_edge_data(u, v).values(), key=lambda x: x['length'])

        # if it has a geometry attribute (ie, a list of line segments)
        if 'geometry' in data:
            # add them to the list of lines to plot
            xs, ys = data['geometry'].xy
            lines.append(list(zip(xs, ys)))
        else:
            # if it doesn't have a geometry attribute, the edge is a straight
            # line from node to node
            x1 = G.nodes[u]['x']
            y1 = G.nodes[u]['y']
            x2 = G.nodes[v]['x']
            y2 = G.nodes[v]['y']
            line = ((x1, y1), (x2, y2))
            lines.append(line)

    return lines


def shortest_path_lines_nx(origin, destination):
    """
    uses the default shortest path algorithm available through networkx

    Parameters
    __________
    :param      origin: int:    node ID
    :param destination: int:    node ID

    Returns
    _______
    :return lines: list:
        [(double, double), ...]:   each tuple represents the bend-point in a straight road
    """

    # yx_car_position = (car['position'][1], car['position'][0])
    # origin = ox.utils.get_nearest_node(G, yx_car_position)
    route = nx.shortest_path(G, origin, destination, weight='length')

    # find the route lines
    edge_nodes = list(zip(route[:-1], route[1:]))
    lines = []
    for u, v in edge_nodes:
        # if there are parallel edges, select the shortest in length
        data = min(G.get_edge_data(u, v).values(), key=lambda x: x['length'])

        # if it has a geometry attribute (ie, a list of line segments)
        if 'geometry' in data:
            # add them to the list of lines to plot
            xs, ys = data['geometry'].xy
            lines.append(list(zip(xs, ys)))
        else:
            # if it doesn't have a geometry attribute, the edge is a straight
            # line from node to node
            x1 = G.nodes[u]['x']
            y1 = G.nodes[u]['y']
            x2 = G.nodes[v]['x']
            y2 = G.nodes[v]['y']
            line = ((x1, y1), (x2, y2))
            lines.append(line)

    return lines
