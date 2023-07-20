# SymBChainSim

### Running the simulation

It is recommended to create a new virtual enviroment with python version 3.11.0
as this version of python was used for developemnt.

Create a virtual enviroment with

conda (recommended): https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

venv: https://docs.python.org/3/library/venv.html

### In the new enviroment navigate to the cloned project:

1) run `pip install -r requirements.txt` to install the required python libraries
2) set desired simulation parameters in Configs/base.yaml. You can use a different file by editing env_vars.yaml (all configs files must be in the Cofigs directory)
3) run `python blockchain.py`

Each module is extensivly described with comments. If the above example executes correctly you can start using it and extending it as necessary for you work.
