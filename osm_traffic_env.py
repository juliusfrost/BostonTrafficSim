import numpy as np
import re
    
from gym.spaces.discrete import Discrete
from gym.spaces.box import Box
from gym.spaces.tuple_space import Tuple

from flow.core import rewards
from flow.envs.base_env import Env

ADDITIONAL_ENV_PARAMS = {
    # minimum switch time for each traffic light (in seconds)
    "switch_time": 2.0,
    # whether the traffic lights should be actuated by sumo or RL
    # options are "controlled" and "actuated"
    "tl_type": "actuated",
    # determines whether the action space is meant to be discrete or continuous
    "discrete": False,
    # list of ids for the traffic lights to be controlled via RL
    # if list is empty, then behavior defaults to the value of tl_type
    "tl_distribution": [],
}

class OSMTrafficEnvironment(Env):
    """Environment used to train traffic lights to regulate traffic flow
    through an arbitrary network.

    Required from env_params:

    * switch_time: minimum switch time for each traffic light (in seconds).
      Earlier RL commands are ignored.
    * tl_type: whether the traffic lights should be actuated by sumo or RL
      options are "controlled" and "actuated"
    * discrete: determines whether the action space is meant to be discrete or
      continuous
    * tl_distribution: which lights specifically are to be controlled with RL

    States
        An observation is the distance of each vehicle to its intersection, a
        number uniquely identifying which edge the vehicle is on, and the speed
        of the vehicle.

    Actions
        The action space consist of a list of float variables ranging from 0-1
        specifying whether a traffic light is supposed to switch or not. The
        actions are sent to the traffic light in the grid from left to right
        and then top to bottom.

    Rewards
        The reward is the negative per vehicle delay minus a penalty for
        switching traffic lights

    Termination
        A rollout is terminated once the time horizon is reached.

    Additional
        Vehicles are rerouted to the start of their original routes once they
        reach the end of the network in order to ensure a constant number of
        vehicles.
    """

    def __init__(self, env_params, sim_params, scenario, simulator='traci'):

        for p in ADDITIONAL_ENV_PARAMS.keys():
            if p not in env_params.additional_params:
                raise KeyError(
                    'Environment parameter "{}" not supplied'.format(p))

        super().__init__(env_params, sim_params, scenario, simulator)

        # self.grid_array = scenario.net_params.additional_params["grid_array"]
        # self.rows = self.grid_array["row_num"]
        # self.cols = self.grid_array["col_num"]
        # self.num_observed = self.grid_array.get("num_observed", 3)
        # self.num_traffic_lights = self.rows * self.cols
        self.tl_type = env_params.additional_params['tl_type']

        self.tl_distribution = env_params.additional_params['tl_distribution']

        # Saving env variables for plotting
        self.steps = env_params.horizon
        # self.obs_var_labels = {
        #     'edges': np.zeros((self.steps, self.k.vehicle.num_vehicles)),
        #     'velocities': np.zeros((self.steps, self.k.vehicle.num_vehicles)),
        #     'positions': np.zeros((self.steps, self.k.vehicle.num_vehicles))
        # }
        # self.node_mapping = scenario.get_node_mapping()


        # when this hits min_switch_time we change from yellow to red
        # the second column indicates the direction that is currently being
        # allowed to flow. 0 is flowing top to bottom, 1 is left to right
        # For third column, 0 signifies yellow and 1 green or red
        self.min_switch_time = env_params.additional_params["switch_time"]

        # if self.tl_type != "actuated":
        #     for i in range(self.rows * self.cols):
        #         self.k.traffic_light.set_state(
        #             node_id='center' + str(i), state="GrGr")
        #         self.last_change[i, 2] = 1

        
        # list of traffic light ids
        self.traffic_lights = self.k.traffic_light.get_ids()
        # number of traffic lights
        self.num_traffic_lights = len(self.traffic_lights)
        # self.num_lights = 0
        # # assign each light an index, each node has a range of indicies assigned
        # self.light_index = dict()
        # for node_id in self.traffic_lights:
        #     try:
        #         # try to get the state (a string of r,y,g lights)
        #         # each traffic light has a number of lights it can control
        #         state = self.k.traffic_light.get_state(node_id)
        #         self.num_lights += len(state)
        #         # for each node assign a range of lights, (inclusive, exclusive)
        #         self.light_index.update({ node_id: (self.num_lights - len(state), self.num_lights) })
        #     except:
        #         # this should not happen and only does because there is a bug in the recent version of flow
        #         print('could not find state for node', node_id)
        #         self.traffic_lights.remove(node_id)
        # print('num_lights', self.num_lights)

        # keeps track of the last time the light was allowed to change.
        self.last_change = np.zeros((self.num_traffic_lights, 3))

        # each traffic light is assigned an index
        # dictionaries that convert an trafic light id to an index and reverse
        self.index_to_tl = dict(zip(range(self.num_traffic_lights), self.traffic_lights))
        self.tl_to_index = dict(zip(self.traffic_lights, range(self.num_traffic_lights)))

        self.edges = self.k.scenario.get_edge_list() + self.k.scenario.get_junction_list()
        self.num_edges = len(self.edges)
        self.edge_to_index = dict(zip(self.edges, range(self.num_edges)))
        self.index_to_edge = dict(zip(range(self.num_edges), self.edges))


        # if the traffic lights are controlled by RL, set their beginning state
        # if self.tl_type == 'controlled':
        #     for node_id in self.traffic_lights:
        #         if len(self.tl_distribution) == 0 or tl_id in self.tl_distribution:
        #             state = self.k.traffic_light.get_state(node_id)
        #             # make all lights green
        #             state = 'g' * len(state)
        #             self.k.traffic_light.set_state(
        #                 node_id=node_id, 
        #                 state=state)


        # # Additional Information for Plotting
        # self.edge_mapping = {"top": [], "bot": [], "right": [], "left": []}
        # for i, veh_id in enumerate(self.k.vehicle.get_ids()):
        #     edge = self.k.vehicle.get_edge(veh_id)
        #     for key in self.edge_mapping:
        #         if key in edge:
        #             self.edge_mapping[key].append(i)
        #             break

        # check whether the action space is meant to be discrete or continuous
        self.discrete = env_params.additional_params.get("discrete", False)

        self.test = env_params.additional_params.get("test", False)

    @property
    def action_space(self):
        """See class definition."""
        if self.test:
            return Box(low=0, high=0, shape=(0,), dtype=np.float32)


        if self.discrete:
            return Discrete(2 ** self.num_traffic_lights)
        else:
            return Box(
                low=-1,
                high=1,
                shape=(self.num_traffic_lights,),
                dtype=np.float32)

    @property
    def observation_space(self):
        """See class definition."""
        if self.test:
            Box(low=0, high=0, shape=(0,), dtype=np.float32)


        speed = Box(
            low=0,
            high=1,
            shape=(self.scenario.vehicles.num_vehicles,),
            dtype=np.float32)
        dist_to_intersec = Box(
            low=0.,
            high=np.inf,
            shape=(self.scenario.vehicles.num_vehicles,),
            dtype=np.float32)
        edge_num = Box(
            low=0.,
            high=1,
            shape=(self.scenario.vehicles.num_vehicles,),
            dtype=np.float32)
        traffic_lights = Box(
            low=0.,
            high=1,
            shape=(3 * self.num_traffic_lights,),
            dtype=np.float32)
        return Tuple((speed, dist_to_intersec, edge_num, traffic_lights))

    def get_state(self):
        """See class definition."""
        if self.test:
            np.array([])


        # get the state arrays
        speeds = [
            self.k.vehicle.get_speed(veh_id) / self.k.scenario.max_speed()
            for veh_id in self.k.vehicle.get_ids()
        ]

        # compute the normalizers
        max_dist = max(self.k.scenario.edge_length(edge) 
            for edge in self.k.scenario.get_edge_list())

        dist_to_intersec = [
            self.get_distance_to_intersection(veh_id) / max_dist
            for veh_id in self.k.vehicle.get_ids()
        ]

        edges = [
            self._convert_edge(self.k.vehicle.get_edge(veh_id)) /
            (self.num_edges - 1)
            for veh_id in self.k.vehicle.get_ids()
        ]

        state = [
            speeds, dist_to_intersec, edges,
            self.last_change.flatten().tolist()
        ]
        return np.array(state)


    def _apply_rl_actions(self, rl_actions):
        """See class definition."""
        if self.test:
            return


        # check if the action space is discrete
        if self.discrete:
            # convert single value to list of 0's and 1's
            rl_mask = [int(x) for x in list('{0:0b}'.format(rl_actions))]
            rl_mask = [0] * (self.num_traffic_lights - len(rl_mask)) + rl_mask
        else:
            # convert values less than 0.5 to zero and above to 1. 0's indicate
            # that should not switch the direction
            rl_mask = rl_actions > 0.0

        for i, action in enumerate(rl_mask):
            # check if our timer has exceeded the yellow phase, meaning it
            # should switch to red
            if self.last_change[i, 2] == 0:  # currently yellow
                self.last_change[i, 0] += self.sim_step
                if self.last_change[i, 0] >= self.min_switch_time:
                    if self.last_change[i, 1] == 0:
                        self.k.traffic_light.set_state(
                            node_id='center{}'.format(i),
                            state="GrGr")
                    else:
                        self.k.traffic_light.set_state(
                            node_id='center{}'.format(i),
                            state='rGrG')
                    self.last_change[i, 2] = 1
            else:
                if action:
                    if self.last_change[i, 1] == 0:
                        self.k.traffic_light.set_state(
                            node_id='center{}'.format(i),
                            state='yryr')
                    else:
                        self.k.traffic_light.set_state(
                            node_id='center{}'.format(i),
                            state='ryry')
                    self.last_change[i, 0] = 0.0
                    self.last_change[i, 1] = not self.last_change[i, 1]
                    self.last_change[i, 2] = 0

    def compute_reward(self, rl_actions, **kwargs):
        """See class definition."""
        if self.test:
            return 0

        return - rewards.min_delay_unscaled(self) \
            - rewards.boolean_action_penalty(rl_actions >= 0.5, gain=1.0)


    # ===============================
    # ============ UTILS ============
    # ===============================

    def record_obs_var(self):
        """
        Records velocities and edges in self.obs_var_labels at each time
        step. This is used for plotting.
        """
        for i, veh_id in enumerate(self.k.vehicle.get_ids()):
            self.obs_var_labels['velocities'][
                self.time_counter - 1, i] = self.k.vehicle.get_speed(veh_id)
            self.obs_var_labels['edges'][self.time_counter - 1, i] = \
                self._convert_edge(self.k.vehicle.get_edge(veh_id))
            x = self.k.vehicle.get_x_by_id(veh_id)
            if x > 2000:  # hardcode
                x = 0
            self.obs_var_labels['positions'][self.time_counter - 1, i] = x

    def get_distance_to_intersection(self, veh_ids):
        """Determines the smallest distance from the current vehicle's position
        to any of the intersections.

        Parameters
        ----------
        veh_ids : str
            vehicle identifier

        Returns
        -------
        tup
            1st element: distance to closest intersection
            2nd element: intersection ID (which also specifies which side of
            the intersection the vehicle will be arriving at)
        """
        if isinstance(veh_ids, list):
            return [self.find_intersection_dist(veh_id) for veh_id in veh_ids]
        else:
            return self.find_intersection_dist(veh_ids)

    def find_intersection_dist(self, veh_id):
        """Return distance from the vehicle's current position to the position
        of the node it is heading toward."""
        edge_id = self.k.vehicle.get_edge(veh_id)

        if edge_id == "":
            raise Exception('no edge found for vehicle ' + veh_id)
        if 'center' in edge_id:
            return 0
        edge_len = self.k.scenario.edge_length(edge_id)
        relative_pos = self.k.vehicle.get_position(veh_id)
        dist = edge_len - relative_pos
        return dist

    def sort_by_intersection_dist(self):
        """Sorts the vehicle ids of vehicles in the network by their distance
        to the intersection.

        Returns
        -------
        sorted_ids : list
            a list of all vehicle IDs sorted by position
        sorted_extra_data : list or tuple
            an extra component (list, tuple, etc...) containing extra sorted
            data, such as positions. If no extra component is needed, a value
            of None should be returned
        """
        ids = self.k.vehicle.get_ids()
        sorted_indx = np.argsort(self.get_distance_to_intersection(ids))
        sorted_ids = np.array(ids)[sorted_indx]
        return sorted_ids

    def _convert_edge(self, edges):
        """Converts the string edge to a number.

        Start at the bottom left vertical edge and going right and then up, so
        the bottom left vertical edge is zero, the right edge beside it  is 1.

        The numbers are assigned along the lowest column, then the lowest row,
        then the second lowest column, etc. Left goes before right, top goes
        before bot.

        The values are are zero indexed.

        Parameters
        ----------
        edges : list of str or str
            name of the edge(s)

        Returns
        -------
        list of int or int
            a number uniquely identifying each edge
        """
        if isinstance(edges, list):
            return [self._split_edge(edge) for edge in edges]
        else:
            return self._split_edge(edges)

    def _split_edge(self, edge):
        """Helper function for convert_edge"""
        return self.edge_to_index[edge]

    def additional_command(self):
        """Used to insert vehicles that are on the exit edge and place them
        back on their entrance edge."""
        # not needed anymore
        # for veh_id in self.k.vehicle.get_ids():
        #     self._reroute_if_final_edge(veh_id)

    def _reroute_if_final_edge(self, veh_id):
        """Checks if an edge is the final edge. If it is return the route it
        should start off at."""
        edge = self.k.vehicle.get_edge(veh_id)
        if edge == "":
            return
        if edge[0] == ":":  # center edge
            return
        pattern = re.compile(r"[a-zA-Z]+")
        edge_type = pattern.match(edge).group()
        edge = edge.split(edge_type)[1].split('_')
        row_index, col_index = [int(x) for x in edge]

        # find the route that we're going to place the vehicle on if we are
        # going to remove it
        route_id = None
        if edge_type == 'bot' and col_index == self.cols:
            route_id = "bot{}_0".format(row_index)
        elif edge_type == 'top' and col_index == 0:
            route_id = "top{}_{}".format(row_index, self.cols)
        elif edge_type == 'left' and row_index == 0:
            route_id = "left{}_{}".format(self.rows, col_index)
        elif edge_type == 'right' and row_index == self.rows:
            route_id = "right0_{}".format(col_index)

        if route_id is not None:
            type_id = self.k.vehicle.get_type(veh_id)
            lane_index = self.k.vehicle.get_lane(veh_id)
            # remove the vehicle
            self.k.vehicle.remove(veh_id)
            # reintroduce it at the start of the network
            self.k.vehicle.add(
                veh_id=veh_id,
                edge=route_id,
                type_id=str(type_id),
                lane=str(lane_index),
                pos="0",
                speed="max")

    def k_closest_to_intersection(self, edges, k):
        """
        Return the veh_id of the k closest vehicles to an intersection for
        each edge. Performs no check on whether or not edge is going toward an
        intersection or not. Does no padding
        """
        if k < 0:
            raise IndexError("k must be greater than 0")
        dists = []

        def sort_lambda(veh_id):
            return self.get_distance_to_intersection(veh_id)

        if isinstance(edges, list):
            for edge in edges:
                vehicles = self.k.vehicle.get_ids_by_edge(edge)
                dist = sorted(
                    vehicles,
                    key=sort_lambda
                )
                dists += dist[:k]
        else:
            vehicles = self.k.vehicle.get_ids_by_edge(edges)
            dist = sorted(
                vehicles,
                key=lambda veh_id: self.get_distance_to_intersection(veh_id))
            dists += dist[:k]
        return dists


class OSMTrafficTestEnvironment(OSMTrafficEnvironment):
    """
    Class that overrides RL methods of OSMTrafficEnvironment so we can test
    construction without needing to specify RL methods
    """

    def _apply_rl_actions(self, rl_actions):
        """See class definition."""
        pass

    def compute_reward(self, rl_actions, **kwargs):
        """No return, for testing purposes."""
        return 0


