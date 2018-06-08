(let [x1 (sample (normal 0 1))
      x2 (sample (normal 0 1))
      cov [[1 0] [0 1]]
      y [1 1]]
  (if (> x1 0)
    (if (> x2 0)
      (observe (mvn [1 1] cov) y)
      (observe (mvn [1 -1] cov) y))
    (if (> x2 0)
      (observe (mvn [-1 1] cov) y)
      (observe (mvn [-1 -1] cov) y)))
  [x1 x2])