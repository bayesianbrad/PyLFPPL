(let [x1 (sample (normal 0 1))
      y 10]
  (if (> x1 0)
    (let [x2 (sample (normal 0 1))]
      (observe (normal x2 2) y))
    (let [x3 (sample (normal 0 1))]
      (observe (normal x3 2) y)))
  x1)


;(let [x1 (sample (normal 0 1))
;      x2 (sample (normal 0 1))
;      x3 (sample (normal 0 1))
;      y 1]
;  (if (> x1 0)
;    (observe (normal x2 1) y)
;    (observe (normal x3 1) y))
;  (vector x1 x2 x3))