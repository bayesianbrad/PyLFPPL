; (defn observe-data [_ data slope bias]
;      (let [xn (first data)
;            yn (second data)
;            zn (+ (* slope xn) bias)]
;        (observe (normal zn 1.0) yn)
;        (rest (rest data))))
;
;    (let [slope (sample (normal 0.0 100.0))
;          bias  (sample (normal 0.0 100.0))
;          data (vector
;                 1.0 2.1 2.0 3.9 3.0 5.3
;                 4.0 7.7 5.0 10.2 6.0 12.9)]
;      (loop 6 data observe-data slope bias)
;      (vector slope bias))
(defn observe-data [_ data slope bias]
                    ;;_ loop index
                    ;;data value
                    ;;slop and bias are the real args
  (let [xn (first data)
        yn (second data)
        zn (+ (* slope xn) bias)]
    (observe (normal zn 1.0) yn)
    (rest (rest data))))

(let [slope (sample (normal 0.0 100.0))
      bias  (sample (normal 0.0 100.0))
      data (vector
             1.0 2.1 2.0 3.9 3.0 5.3)]
             ;4.0 7.7 5.0 10.2 6.0 12.9)]
  (loop 3 data observe-data slope bias)
   (vector slope bias))