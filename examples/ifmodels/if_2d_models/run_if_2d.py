import tests.unittests.models.ifmodels.if_2d_models.if_2d as test

from pyfo.inference.dhmc import DHMCSampler as dhmc

# model
# print(test.model)
# test.model.display_graph()

## inference
# Note: the mvn likelihood has some issue
dhmc_ = dhmc(test)
burn_in = 10 ** 3
n_sample = 10 ** 3
stepsize_range = [0.03,0.15]
n_step_range = [4, 15]
n_chain = 5

# stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range,
#                      plot=True, print_stats=True, save_samples=True, plot_ac=True)

all_stats = dhmc_.sample_multiple_chains(n_chains=n_chain, n_samples=n_sample,burn_in=burn_in,
                                         stepsize_range=stepsize_range,n_step_range=n_step_range, save_samples=True)