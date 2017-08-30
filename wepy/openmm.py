
import simtk.openmm.app as omma
import simtk.openmm as omm
import simtk.unit as unit

from wepy.walker import Walker
from wepy.runner import Runner

# for the sim manager, dependencies will change
import sys
import os
from collections import namedtuple

import numpy as np
import pandas as pd
import h5py

from wepy.sim_manager import Manager

# default inputs
from wepy.resampling.resampler import NoResampler
from wepy.runner import NoRunner
from wepy.boundary_conditions.boundary import NoBC


class OpenMMRunner(Runner):

    def __init__(self, system, topology):
        self.system = system
        self.topology = topology

    def run_segment(self, walker, segment_length):

        # TODO can we do this outside of this?
        # instantiate an integrator
        integrator = omm.LangevinIntegrator(300*unit.kelvin,
                                            1/unit.picosecond,
                                            0.002*unit.picoseconds)

        # instantiate a simulation object
        simulation = omma.Simulation(self.topology, self.system, integrator)

        # initialize the positions
        simulation.context.setPositions(walker.positions)

        # run the simulation segment for the number of time steps
        simulation.step(segment_length)

        # save the state of the system with all possible values
        new_state = simulation.context.getState(getPositions=True,
                                            getVelocities=True,
                                            getParameters=True,
                                            getParameterDerivatives=False,
                                            getForces=False,
                                            getEnergy=False,
                                            enforcePeriodicBox=False
                                            )

        # create a new walker for this
        new_walker = OpenMMWalker(new_state, walker.weight)

        return new_walker

class OpenMMRunnerParallel(Runner):

    def __init__(self, system, topology):
        self.system = system
        self.topology = topology

    def run_segment(self, walker, segment_length, gpu_index):

        try:
            # instantiate a CUDA platform with gpu_index number
            platform = omm.Platform.getPlatformByName('CUDA')
            platform.setPropertyDefaultValue('Precision', 'mixed')
            platform.setPropertyDefaultValue('DeviceIndex',str(gpu_index))

            # instantiate an integrator
            integrator = omm.LangevinIntegrator(300*unit.kelvin,
                                                1/unit.picosecond,
                                                0.002*unit.picoseconds)

            # instantiate a simulation object
            simulation = omma.Simulation(self.topology, self.system, integrator, platform)

            # initialize the positions
            simulation.context.setPositions(walker.positions)
            simulation.context.setVelocities(walker.velocities)

            # run the simulation segment for the number of time steps
            simulation.step(segment_length)

            # save the state of the system with all possible values
            new_state = simulation.context.getState(getPositions=True,
                                            getVelocities=True,
                                            getParameters=True,
                                            getParameterDerivatives=True,
                                            getForces=True,
                                            getEnergy=True,
                                            enforcePeriodicBox=True
                                            )

            # create a new walker for this
            new_walker = OpenMMWalker(new_state, walker.weight)

            return new_walker

        except:
            print ('gpu_index ={} failed'.format(gpu_index))
            return  None





class OpenMMWalker(Walker):

    def __init__(self, state, weight):
        super().__init__(state, weight)

    @property
    def positions(self):
        return self.state.getPositions()

    @property
    def velocities(self):
        return self.state.getVelocities()

    @property
    def forces(self):
        return self.state.getForces()

    @property
    def kinetic_energy(self):
        return self.state.getKineticEnergy()

    @property
    def potential_energy(self):
        return self.state.getPotentialEnergy()

    @property
    def time(self):
        return self.state.getTime()

    @property
    def box_vectors(self):
        return self.state.getPeriodicBoxVectors()

    @property
    def box_volume(self):
        return self.state.getPeriodicBoxVolume()

    @property
    def parameters(self):
        return self.state.getParameters()

    @property
    def parameter_derivatives(self):
        return self.state.getEnergyParameterDerivatives()

# class OpenMMManager(Manager):
#     def __init__(self, init_walkers, num_workers,
#                  runner = NoRunner(),
#                  resampler = NoResampler(),
#                  ubc = NoBC(),
#                  work_mapper = map):
#         super().__init__(init_walkers, num_workers,
#                         runner,
#                         resampler,
#                         work_mapper)
#         self.ubc = ubc

#     def run_simulation(self, n_cycles, segment_lengths, debug_prints=False):
#         """Run a simulation for a given number of cycles with specified
#         lengths of MD segments in between.

#         Can either return results in memory or write to a file.
#         """


#         if debug_prints:
#             sys.stdout.write("Starting simulation\n")
#         walkers = self.init_walkers

#         resampling_handler = pd.HDFStore(os.getcwd()+'/resampling_records.h5',mode='w')
#         walker_handler = h5py.File(os.getcwd()+'/walkers_records.h5',mode='w')
#         dist_handler = h5py.File(os.getcwd()+'/dist_records.h5',mode='w')
#         #save initial state
#         self.save_walker_records(walker_handler,-1, walkers)
#         for cycle_idx in range(n_cycles):
#             if debug_prints:
#                 sys.stdout.write("Begin cycle {}\n".format(cycle_idx))


#             # run the segment

#             walkers = self.run_segment(walkers, segment_lengths[cycle_idx],
#                                            debug_prints=debug_prints)


#             # calls wexplore2 ubinding boundary conditions
#             if debug_prints:
#                 sys.stdout.write("Start  boundary Conditions")


#             resampled_walkers, warped_walkers_records, ubc_data= self.ubc.warp_walkers(walkers)
#             # ubc_data is min_distances
#             # record changes in state of the walkers
#             if debug_prints:
#                 sys.stdout.write("End  BoundaryConditions")
#                 print ('warped_walkers=',warped_walkers_records)

#             if debug_prints:
#                 sys.stdout.write("Start Resampling")


#             # resample based walkers
#             resampled_walkers, cycle_resampling_records, resample_data = \
#                             self.resampler.resample(resampled_walkers, debug_prints=debug_prints)

#             # resample_data includes distance_matrix and last_spread
#             self.save_dist_records(dist_handler,cycle_idx, resample_data, ubc_data)

#             # save resampling records in a hdf5 file
#             self.save_resampling_records(resampling_handler,
#                                          cycle_idx,
#                                          cycle_resampling_records,
#                                          warped_walkers_records)
#             if debug_prints:
#                 sys.stdout.write("End  Resampling")

#             # prepare resampled walkers for running new state changes
#             # save walkers positions in a hdf5 file
#             self.save_walker_records(walker_handler, cycle_idx, resampled_walkers)
#             walkers = resampled_walkers.copy()

#         # saving last velocities
#         for walker_idx, walker  in enumerate(resampled_walkers):
#             walker_handler.create_dataset(
#                 'cycle_{:0>5}/walker_{:0>5}/velocities'.format(cycle_idx,walker_idx),
#                 data = self.mdtraj_positions(walker.velocities))

#         resampling_handler.close()
#         walker_handler.close()
#         dist_handler.close()
#         if debug_prints:
#             sys.stdout.write("End cycle {}\n".format(cycle_idx))


#     def mdtraj_positions(self, openmm_positions):

#         n_atoms = len (openmm_positions)

#         xyz = np.zeros(( n_atoms, 3))



#         for i in range(n_atoms):
#             xyz[i,:] = ([openmm_positions[i]._value[0], openmm_positions[i]._value[1],
#                                                     openmm_positions[i]._value[2]])

#         return xyz

#     def save_resampling_records(self, hdf5_handler,
#                                 cycle_idx,
#                                 cycle_resampling_records,
#                                 warped_walkers_records):

#         # save resampling records in table format in a hdf5 file
#         DFResamplingRecord = namedtuple("DFResamplingRecord", ['cycle_idx', 'step_idx',
#                                                                'walker_idx', 'decision',
#                                                                'instruction', 'warped_walker'])
#         df_recs = []
#         warped_walkers_idxs =[]
#         for record in warped_walkers_records:
#             warped_walkers_idxs.append(record[0])

#         for step_idx, step in enumerate(cycle_resampling_records):
#             for walker_idx, rec in enumerate(step):

#                 if  walker_idx  in warped_walkers_idxs:
#                     decision = True
#                 else:
#                     decision = False
#                 df_rec = DFResamplingRecord(cycle_idx=cycle_idx,
#                                             step_idx=step_idx,
#                                             walker_idx=walker_idx,
#                                             decision=rec.decision.name,
#                                             instruction = rec.value,
#                                             warped_walker = decision)
#                 df_recs.append(df_rec)

#         resampling_df = pd.DataFrame(df_recs)

#         hdf5_handler.put('cycle_{:0>5}'.format(cycle_idx), resampling_df, data_columns= True)
#         hdf5_handler.flush(fsync=True)




#     def save_walker_records(self, walker_handler, cycle_idx, resampled_walkers):

#         walker_handler.create_dataset('cycle_{:0>5}/time'.format(cycle_idx),
#                                       data=resampled_walkers[0].time._value)
#         for walker_idx, walker in enumerate(resampled_walkers):
#             walker_handler.create_dataset(
#                 'cycle_{:0>5}/walker_{:0>5}/positions'.format(cycle_idx,walker_idx),
#                                           data = self.mdtraj_positions(walker.positions))
#             box_vector = np.array(((walker.box_vectors._value[0],
#                                     walker.box_vectors._value[1],
#                                     walker.box_vectors._value[2])))
#             walker_handler.create_dataset(
#                 'cycle_{:0>5}/walker_{:0>5}/box_vectors'.format(cycle_idx,walker_idx),
#                 data=box_vector)
#             walker_handler.create_dataset(
#                 'cycle_{:0>5}/walker_{:0>5}/weight'.format(cycle_idx,walker_idx),
#                 data=walker.weight)

#             walker_handler.flush()


#     def read_resampling_data(self,):

#         hdf = pd.HDFStore(os.getcwd()+'/resampling_records.h5',
#                             mode ='r')
#         keys = list (hdf.keys())
#         for key in keys:
#             df = hdf.get(key)
#             print (df)
#         hdf.close()

#     def save_dist_records(self, dist_handler,cycle_idx, resample_data, ubc_data):
#         dist_handler.create_dataset(
#             'cycle_{:0>5}/dist_matrix'.format(cycle_idx),
#             data=resample_data['distance_matrix'])
#         dist_handler.create_dataset(
#             'cycle_{:0>5}/spread'.format(cycle_idx),
#             data=resample_data['spread'])
#         dist_handler.create_dataset(
#             'cycle_{:0>5}/min_distances'.format(cycle_idx),
#             data=ubc_data['min_distances'])

#         dist_handler.flush()
