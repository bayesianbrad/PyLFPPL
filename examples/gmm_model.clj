(defn sample-components [pi]
  (sample (categorical pi)))

(defn observe-data [y z mus]
  (let [mu (get mus z)]
    (observe (normal mu 2) y)))

(let [ys (vector -2.0  -2.5  -1.7  -1.9  -2.2
                  1.5   2.2   3.0   1.2   2.8)
      pi [0.5 0.5]
      zs  (map sample-components (repeat 10 pi))
      mus (vector (sample (normal 0 2))
                  (sample (normal 0 2)))]
  (for [[y z] (interleave ys zs)] (observe-data y z mus))
  (vector mus zs))