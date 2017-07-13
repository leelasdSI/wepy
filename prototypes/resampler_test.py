from wepy.walker import Walker
from wepy.resampling.resampler import RandomCloneMergeResampler

n_walkers = 8
init_weight = 1.0 / n_walkers

init_walkers = [Walker(i, init_weight) for i in range(n_walkers)]


resampler = RandomCloneMergeResampler(12312535346)

# make a template string for pretty printing results as we go
result_template_str = "|".join(["{:^10}" for i in range(n_walkers)])

# print the initial walkers
print("The initial walkers:")
walker_state_str = result_template_str.format(
    *[str(walker.state) for walker in init_walkers])
print(walker_state_str)
walker_weight_str = result_template_str.format(
    *[str(walker.weight) for walker in init_walkers])
print(walker_weight_str)

# do resampling of the initial walkers
resampled_walkers = []
resampling_records = []
walkers = init_walkers
for i in range(3):
    print("---------------------------------------------------------------------------------------")
    print("cycle: {}".format(i))
    # do resampling
    cycle_walkers, cycle_records = resampler.resample(walkers, debug_prints=True)

    # save the walkers
    resampled_walkers.append(cycle_walkers)
    # save the resampling records
    resampling_records.append(cycle_records)

    # print results for this cycle
    print("Net state of walkers after resampling:")
    print("--------------------------------------")
    walker_state_str = result_template_str.format(
        *[str(walker.state) for walker in cycle_walkers])
    print(walker_state_str)
    walker_weight_str = result_template_str.format(
        *[str(walker.weight) for walker in cycle_walkers])
    print(walker_weight_str)
