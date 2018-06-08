(let [x (sample (normal 1.0 5.0))
      y 7.0]
  (observe (normal x 2.0) y)
  y)