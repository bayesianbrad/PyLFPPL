(defn observe-data [data slope bias]
  (let [[xn yn] data
        zn (+ (* slope xn) bias)]
    (observe (normal zn 1.0) yn)))

(let [slope (sample (normal 0.0 10.0))
      bias  (sample (normal 0.0 10.0))
      data  (vector [1.0 2.1] [2.0 3.9] [3.0 5.3])]
  (for [i data]
    (observe-data i slope bias))
  (vector slope bias))