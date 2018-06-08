(let [x2 (sample (binomial  1 [0.5]))
      x1 (sample (binomial  1 [0.8]))
      x3 (sample (binomial  1 [0.1]))
      x4 (sample (binomial  1 [0.1]))
       x5 (sample (binomial  1 [0.27]))
       x6 (sample (binomial  1 [0.69]))
       x7 (sample (binomial  1 [0.332]))
      x8 (sample (binomial  1 [0.43]))]
  x2 x1 x3 x4 x5 x6 x7 x8)

;(let  [x3  (sample (binomial  1 [0.69]))]
;  x3)