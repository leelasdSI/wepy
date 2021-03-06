from copy import copy
import pickle

import numpy as np
from scipy.spatial.distance import euclidean

import simtk.openmm.app as omma
import simtk.openmm as omm
import simtk.unit as unit

import mdtraj as mdj

from openmmtools.testsystems import LennardJonesPair

# components for the apparatus
from wepy.resampling.distances.distance import Distance
from wepy.resampling.resamplers.wexplore import WExploreResampler
from wepy.boundary_conditions.unbinding import UnbindingBC
from wepy.runners.openmm import OpenMMRunner, OpenMMState
from wepy.walker import Walker
from wepy.runners.openmm import UNIT_NAMES, GET_STATE_KWARG_DEFAULTS
from wepy.reporter.hdf5 import WepyHDF5Reporter
from wepy.reporter.wexplore.dashboard import WExploreDashboardReporter
from wepy.reporter.restree import ResTreeReporter
from wepy.util.mdtraj import mdtraj_to_json_topology

## PARAMETERS

# Platform used for OpenMM which uses different hardware computation
# kernels. Options are: Reference, CPU, OpenCL, CUDA.

# we use the Reference platform because this is just a test
PLATFORM = 'Reference'

# Langevin Integrator
TEMPERATURE= 300.0*unit.kelvin
FRICTION_COEFFICIENT = 1/unit.picosecond
# step size of time integrations
STEP_SIZE = 0.002*unit.picoseconds

# Resampler parameters

# the maximum weight allowed for a walker
PMAX = 0.5
# the minimum weight allowed for a walker
PMIN = 1e-12

# the maximum number of regions allowed under each parent region
MAX_N_REGIONS = (10, 10, 10, 10)

# the maximum size of regions, new regions will be created if a walker
# is beyond this distance from each voronoi image unless there is an
# already maximal number of regions
MAX_REGION_SIZES = (1, 0.5, .35, .25) # nanometers

# boundary condition parameters

# maximum distance between between any atom of the ligand and any
# other atom of the protein, if the shortest such atom-atom distance
# is larger than this the ligand will be considered unbound and
# restarted in the initial state
CUTOFF_DISTANCE = 1.0 # nm

# reporting parameters

# these are the properties of the states (i.e. from OpenMM) which will
# be saved into the HDF5
SAVE_FIELDS = ('positions', 'box_vectors', 'velocities')
# these are the names of the units which will be stored with each
# field in the HDF5
UNITS = UNIT_NAMES

# orchestration parameters
N_WALKERS = 48


## System and OpenMMRunner

# make the test system from openmmtools
test_sys = LennardJonesPair()

# make the integrator
integrator = omm.LangevinIntegrator(TEMPERATURE, FRICTION_COEFFICIENT, STEP_SIZE)

# make a context and set the positions
context = omm.Context(test_sys.system, copy(integrator))
context.setPositions(test_sys.positions)

# get the data from this context so we have a state to start the
# simulation with
get_state_kwargs = dict(GET_STATE_KWARG_DEFAULTS)
init_sim_state = context.getState(**get_state_kwargs)
init_state = OpenMMState(init_sim_state)

# initialize the runner
runner = OpenMMRunner(test_sys.system, test_sys.topology, integrator, platform=PLATFORM)

## Distance Metric
# we define a simple distance metric for this system, assuming the
# positions are in a 'positions' field
class PairDistance(Distance):

    def __init__(self, metric=euclidean):
        self.metric = metric

    def image(self, state):
        return state['positions']

    def image_distance(self, image_a, image_b):
        dist_a = self.metric(image_a[0], image_a[1])
        dist_b = self.metric(image_b[0], image_b[1])

        return np.abs(dist_a - dist_b)


# make a distance object which can be used to compute the distance
# between two walkers, for our scorer class
distance = PairDistance()

## Resampler
resampler = WExploreResampler(distance=distance,
                               init_state=init_state,
                               max_region_sizes=MAX_REGION_SIZES,
                               max_n_regions=MAX_N_REGIONS,
                               pmin=PMIN, pmax=PMAX)

## Boundary Conditions

# the mdtraj here is needed for the distance function
mdtraj_topology = mdj.Topology.from_openmm(test_sys.topology)

## Reporters if we want them
json_str_top = mdtraj_to_json_topology(mdtraj_topology)

# initialize the unbinding boundary conditions
ubc = UnbindingBC(cutoff_distance=CUTOFF_DISTANCE,
                  initial_state=init_state,
                  topology=json_str_top,
                  ligand_idxs=np.array(test_sys.ligand_indices),
                  receptor_idxs=np.array(test_sys.receptor_indices))

# make a dictionary of units for adding to the HDF5
units = dict(UNIT_NAMES)

hdf5_reporter_kwargs = {'save_fields' : SAVE_FIELDS,
                        'resampler' : resampler,
                        'boundary_conditions' : ubc,
                        'topology' : json_str_top,
                        'units' : units}

dashboard_reporter_kwargs = {'step_time' : STEP_SIZE.value_in_unit(unit.second),
                             'max_n_regions' : resampler.max_n_regions,
                             'max_region_sizes' : resampler.max_region_sizes,
                             'bc_cutoff_distance' : ubc.cutoff_distance}

# Resampling Tree
restree_reporter_kwargs = {'resampler' : resampler,
                           'boundary_condition' : ubc,
                           'node_radius' : 3.0,
                           'row_spacing' : 5.0,
                           'step_spacing' : 20.0,
                           'progress_key' : 'min_distances',
                           'max_progress_value' : ubc.cutoff_distance,
                           'colormap_name' : 'plasma'}


reporter_classes = [WepyHDF5Reporter, WExploreDashboardReporter,
                    ResTreeReporter]
reporter_kwargs = [hdf5_reporter_kwargs, dashboard_reporter_kwargs,
                   restree_reporter_kwargs]


from wepy.work_mapper.mapper import Mapper

from wepy.orchestration.orchestrator import WepySimApparatus, Orchestrator
from wepy.orchestration.configuration import Configuration

sim_apparatus = WepySimApparatus(runner, resampler=resampler,
                                 boundary_conditions=ubc)

# we also create a default configuration for the orchestrator that
# will be used unless one is given at runtime for the creation of a
# simulation manager
configuration = Configuration(n_workers=4,
                              reporter_classes=reporter_classes,
                              reporter_partial_kwargs=reporter_kwargs)

# we also want to set up the orchestrator with some default walkers to
# use to get us started. Otherwise these could be provided from a
# snapshot or on their own. Ideally we only want to have a single
# script setting up an orchestrator and then manage everything else on
# the command line intereactively from then on out
init_weight = 1.0 / N_WALKERS
init_walkers = [Walker(OpenMMState(init_sim_state), init_weight) for i in range(N_WALKERS)]

# then create the seed/root/master orchestrator which will be used
# from here on out
orchestrator = Orchestrator(sim_apparatus,
                            default_init_walkers=init_walkers,
                            default_configuration=configuration)


# save it
orchestrator.dump('LJ-pair.orch', mode='wb')

