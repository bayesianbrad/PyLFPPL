(let [x0 (sample (normal 0 1))
    x (sample (normal x0 1))
    ]
    (if (> x 0)
    (observe (normal x 1) 1)
    (observe (normal x 2) 1))
   [ x0 x])