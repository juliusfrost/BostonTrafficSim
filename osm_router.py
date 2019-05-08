from flow.controllers.base_routing_controller import BaseRouter

import random

class OSMRouter(BaseRouter):
    """A router used to continuously re-route vehicles in an OSM scenario.

    This class allows the vehicle to pick a random route at junctions.
    """

    def choose_route(self, env):
        """See parent class."""
        
        # list of all vehicles
        vehicles = env.k.vehicle
        
        # current vehicle id
        veh_id = self.veh_id
        
        # current edge the our vehicle is on
        # ex. 240745677#4
        veh_edge = vehicles.get_edge(veh_id)
        
        # the vehicle's current route, a list of edges
        # ex. ['240745677#3', '240745677#4', '519868599#0']
        veh_route = vehicles.get_route(veh_id)
        
        # list of edge and lane tuples branching from the current edge
        # ex. [(':61450281_2', 0), (':61450281_3', 0)]
        veh_next_edge = env.k.scenario.next_edge(veh_edge,
                                                 vehicles.get_lane(veh_id))
        not_an_edge = ":"
        
        # if there are no next edges from the current edge we are at a dead end
        if len(veh_next_edge) == 0:
            return None
        
        # if we are on the last edge of the route, then we must reroute to prevent the vehicle from stopping
        if veh_route[-1] == veh_edge:
            random_route = random.randint(0, len(veh_next_edge) - 1)
            while veh_next_edge[random_route][0][0] == not_an_edge:
                veh_next_edge = env.k.scenario.next_edge(
                    veh_next_edge[random_route][0],
                    veh_next_edge[random_route][1])
                random_route = random.randint(0, len(veh_next_edge) - 1)
            next_route = [veh_edge, veh_next_edge[random_route][0]]
        else:
            next_route = None
        
        return next_route