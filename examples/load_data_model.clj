(def data (load "test_data"))

(let [ones (first data)
      twos (second data)
      i (sample (categorical ones))
      x (get twos i)]
  (observe (normal 15 2) x)
  x)