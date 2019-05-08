import random
import re
import numpy as np

# the Experiment class is used for running simulations
from flow.core.experiment import Experiment

# all other imports are standard
from flow.core.params import VehicleParams
from flow.core.params import NetParams
from flow.core.params import InitialConfig
from flow.core.params import EnvParams
from flow.core.params import SumoParams

from flow.scenarios import Scenario

from flow.controllers.car_following_models import IDMController
from flow.core.params import InFlows

from osm_router import OSMRouter
from osm_scenario import OSMScenario
import osm_traffic_env
from osm_traffic_env import OSMTrafficEnvironment


# add inflows
inflow = InFlows()
inflow.add(
    veh_type="human",
    edge='241028354',
    vehs_per_hour=1000,
    departSpeed=10,
    departLane="random",
    departPos="last")
inflow.add(
    veh_type="human",
    edge='-240745552',
    vehs_per_hour=700,
    departSpeed=10,
    departLane="random",
    departPos="last")
inflow.add(
    veh_type="human",
    edge='519869879#1',
    vehs_per_hour=700,
    departSpeed=10,
    departLane="random",
    departPos="last")
inflow.add(
    veh_type="human",
    edge='86479790#2',
    vehs_per_hour=500,
    departSpeed=10,
    departLane="random",
    departPos="last")
inflow.add(
    veh_type="human",
    edge='8649389#1',
    vehs_per_hour=200,
    departSpeed=10,
    departLane="random",
    departPos="last")
inflow.add(
    veh_type="human",
    edge='8649816#9',
    vehs_per_hour=200,
    departSpeed=10,
    departLane="random",
    departPos="last")

initial_config = InitialConfig(
    spacing="random", 
    perturbation=1
)

net_params = NetParams(
    inflows=inflow,
    osm_path='Kenmore.osm',
    no_internal_links=False
)

# create the remainding parameters
env_params = EnvParams()
env_params.additional_params = osm_traffic_env.ADDITIONAL_ENV_PARAMS
sim_params = SumoParams(render=True, restart_instance=True)
# initial_config = InitialConfig()
vehicles = VehicleParams()
vehicles.add('human',
             num_vehicles=100, 
             acceleration_controller=(IDMController, {}),
             routing_controller=(OSMRouter, {}))

# create the scenario
scenario = OSMScenario(
    name='Kenmore',
    net_params=net_params,
    initial_config=initial_config,
    vehicles=vehicles
)

# create the environment
env = OSMTrafficTestEnvironment(
    env_params=env_params,
    sim_params=sim_params,
    scenario=scenario
)

# run the simulation for 1000 steps
exp = Experiment(env=env)
exp.run(1, 1000)