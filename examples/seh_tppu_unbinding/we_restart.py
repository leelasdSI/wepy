import pickle

with open('./outputs/restart.pkl', 'rb') as rf:
    restarter = pickle.load(rf)

sim_manager = restarter.new_sim_manager()


def main(continue_run, n_cycles, steps, n_walkers, n_workers=1, debug_prints=False, seed=None):

    ### RUN the simulation
    print("Starting run")
    sim_manager.continue_run_simulation(continue_run, n_cycles, steps, debug_prints=True)
    print("Finished run")

if __name__ == "__main__":

    import time
    import multiprocessing as mp
    import sys
    import logging

    # needs to call spawn for starting processes due to CUDA not
    # tolerating fork
    mp.set_start_method('spawn')
    mp.log_to_stderr(logging.INFO)

    if sys.argv[1] == "--help" or sys.argv[1] == '-h':
        print("arguments: continue_run_idx, n_cycles, n_steps, n_walkers, n_workers")
    else:

        continue_run = int(sys.argv[1])
        n_cycles = int(sys.argv[2])
        n_steps = int(sys.argv[3])
        n_walkers = int(sys.argv[4])
        n_workers = int(sys.argv[5])

        print("Number of steps: {}".format(n_steps))
        print("Number of cycles: {}".format(n_cycles))

        steps = [n_steps for i in range(n_cycles)]

        start = time.time()
        main(continue_run, n_cycles, steps, n_walkers, n_workers=n_workers,
             debug_prints=True)
        end = time.time()

        print("time {}".format(end-start))

    if sys.argv[1] == "--help" or sys.argv[1] == '-h':
        print("arguments: n_runs, n_cycles, n_steps, n_walkers, n_workers")
    else:

        n_runs = int(sys.argv[1])
        n_cycles = int(sys.argv[2])
        n_steps = int(sys.argv[3])
        n_walkers = int(sys.argv[4])
        n_workers = int(sys.argv[5])

        print("Number of steps: {}".format(n_steps))
        print("Number of cycles: {}".format(n_cycles))

        steps = [n_steps for i in range(n_cycles)]

        start = time.time()
        main(n_runs, n_cycles, steps, n_walkers, n_workers, debug_prints=True)
        end = time.time()

        print("time {}".format(end-start))
