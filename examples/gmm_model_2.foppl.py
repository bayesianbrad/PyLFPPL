from foppl import *

def sample_components(pi):
    return sample(categorical(pi))

def observe_data(y, z, mus):
    mu = mus[z]
    observe(normal(mu, 2), y)

ys = [-2.0, -2.5, -1.7, -1.9, -2.2, 1.5, 2.2, 3.0, 1.2, 2.8]
pi = [0.5, 0.5]
zs = map(sample_components, pi * 10)
mus = [sample(normal(0, 2)), sample(normal(0, 2))]
for y, z in interleave(ys, zs):
    observe_data(y, z, mus)
[mus, zs]
