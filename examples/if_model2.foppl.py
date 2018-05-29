x1 = sample(normal(0, 2))
x2 = sample(normal(0, 4))
if x1 > 0:
    observe(normal(x2, 1), 1)
else:
    observe(normal(-1, 1), 1)
