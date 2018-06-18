;(defn obs-step [n ys e l s]
;  (if (< (+ n 1) s )
;    (observe (exponential e) (first ys))
;    (observe (exponential l) (first ys)))
;  (rest ys))
;
;(let [e (sample (exponential 1))
;      l (sample (exponential 1))
;      T 10
;      s (sample (uniform 0 10))
;      ys (vector 4 5 4 4 1 0 0 1 0 1)]
;  (loop 10 ys obs-step e l s)
;  (vector e l s))

(defn obs-step [n ys e l s]
  (if (< (+ n 1) s )
    (observe (exponential e) (get ys n))
    (observe (exponential l) (get ys n)))
  ys)

(let [e (sample (exponential 1))
      l (sample (exponential 1))
      T 10
      s (sample (uniform 0 10))
      ys (vector 4 5 4 4 1 0 0 1 0 1)]
  (loop 10 ys obs-step e l s)
  (vector e l s))



