(defn observe-data [_ data slope bias]
  (let [xn (first data)
        yn (second data)
        zn (+ (* slope xn) bias)]
    (observe (normal zn 1.0) yn)
    (rest (rest data))))

(let [slope (sample (normal 0.0 10.0))
      bias  (sample (normal 0.0 10.0))
      data  (vector 1.0 2.1 2.0 3.9 3.0 5.3)]
  (loop 3 data observe-data slope bias)
   (vector slope bias))