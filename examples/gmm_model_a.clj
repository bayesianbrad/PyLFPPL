(defn sample-components [pi]
  (sample (categorical pi)))

(defn observe-data [n _ ys zs mus]
  (let [y (get ys n)
        z (get zs n)
        mu (get mus z)]
    (observe (normal mu 1) y)
    nil))

(let [ys (vector -2.0  -2.5  -1.7  -1.9  -2.2
                  1.5   2.2   3.0   1.2   2.8)
      pi [0.5 0.5]
      zs  (repeatedly 10 (sample-components pi))
      mus (vector (sample (normal 0 100))   ; std = 10
                  (sample (normal 0 100)))]
  (loop 10 nil observe-data ys zs mus)
  (vector mus zs))