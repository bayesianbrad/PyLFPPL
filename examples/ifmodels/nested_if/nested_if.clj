(let [x1 (sample (normal 0 1))
      x2 (sample (categorical [0.1 0.2 0.7]))
      y1 7]
  (if (> x1 0)
    (if (> x2 1)
      (observe (normal x1 1) y1)
      (observe (normal (+ x1 x2) 2) y1))
    (observe (normal x2 1) y1) )
  [x1 x2])