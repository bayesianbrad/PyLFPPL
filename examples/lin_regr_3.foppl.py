from foppl import *  # ignored by the compiler, but keeps the IDE happy

def observe_data(data, slope, bias):
    xn = data[0]
    yn = data[1]
    zn = slope * xn + bias
    observe(normal(zn, 1.0), yn)

slope = sample(normal(0.0, 10.0))
bias  = sample(normal(0.0, 10.0))
data  = [[1.0, 2.1], [2.0, 3.9], [3.0, 5.3]]
for i in data:
    observe_data(i, slope, bias)
[slope, bias]
