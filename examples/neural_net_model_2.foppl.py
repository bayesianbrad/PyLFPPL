from foppl import *

latent_dim = 2
hidden_dim = 10
output_dim = 5

def gaussian():
    return sample(normal(0.0, 1.0))

def make_latent_vector():
    return [gaussian() for _ in range(latent_dim)]

def make_hidden_vector():
    return [gaussian() for _ in range(hidden_dim)]

def make_output_vector():
    return [gaussian() for _ in range(output_dim)]

def relu(v):
    return matrix.mul(matrix.ge(v, 0.0), v)

def sigmoid(v):
    return matrix.div(1.0, matrix.add(1.0, matrix.exp(matrix.sub(0.0, v))))

def flip(i, p):
    return sample(binomial(p[i]))

z = make_latent_vector()
W = [make_latent_vector() for _ in range(hidden_dim)]
b = make_hidden_vector()
h = relu(matrix.add(matrix.mmul(W, z), b))

V = [make_hidden_vector() for _ in range(output_dim)]
c = make_output_vector()

result = []
for i in range(output_dim):
    result.append( flip(i, sigmoid(matrix.add(matrix.mmul(V, h), c))) )
