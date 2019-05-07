# BostonTrafficSim

## About
This project attempts to train a reinforcement learning agent in traffic simulation. The RL agent tries to maximize flow in a traffic network of intersections. The multiple car agents drive through the intersections appropriately. The environment is Kenmore Square intersection in Boston.

## Requirements
- [Flow](https://github.com/flow-project/flow)

## Installation
Install Flow with docker:
https://flow.readthedocs.io/en/latest/flow_setup.html#remote-installation-using-docker  
Make sure you are able to access the virtual machine through your browser. Instructions in the link provided.

After opening a terminal window in your browser, do  
`cd flow`
`git pull`  

Then go back to the home directory and clone this repository  
`cd ..`  
`git clone https://github.com/juliusfrost/BostonTrafficSim.git`

## Running

In the virtual environment,  
`cd BostonTrafficSim`  
`jupyter notebook --NotebookApp.token=admin --ip 0.0.0.0 --allow-root`

On your computer, go to `localhost:8888/tree`  
Navigate to `main.ipynb` in the repository and run the cells 



