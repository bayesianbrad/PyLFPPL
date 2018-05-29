(defn relu [v]
  (matrix/mul (matrix/ge v 0.0) v))

(let [weight-prior (normal 0 1)
      W (repeatedly 4 (repeatedly 2 (sample weight-prior)))
      b (repeatedly 4 (sample weight-prior))
      V (repeatedly 5 (repeatedly 4 (sample weight-prior)))
      c (repeatedly 5 (sample weight-prior))
      data-1 [[0 1] [1 0] [0 1]]
      data-2 [[0.45  2.32 7.23 -1.40 0.01]
              [4.45 -3.20 0.78 -9.40 1.11]
              [8.10  5.13 3.90 -6.31 7.41]]]

  (for-each [z data-1
             y data-2]
    (let [h  (relu (matrix/add (matrix/mmul W z) b))
          mu (matrix/add (matrix/mmul V h) c)]
      (for-each [yd y
                 mud mu]
        (observe (normal mud 1) yd))))
  [W b V c])