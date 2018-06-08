(let [z (sample (normal 0 1))
      q (sample (normal 0 1))
      y (if (< z q )
          (sample (normal 0 1))
          (sample (normal 0 2))) ]
  (observe (normal y 1 ) 0.5)
  z q y)

;Equivilent stan model
;q ~ normal(0, 1);
;     z ~ normal(0,1);
;
;     if (z < q)
;        {y ~ normal(0, 1);
;        target += normal_lpdf(y | 0,1) +  normal_lpdf(q | 0, 1) + normal_lpdf(z | 0,1);}
;     else
;         {y ~ normal(0,2);
;         target += normal_lpdf(y | 0,2) +  normal_lpdf(q | 0, 1) + normal_lpdf(z | 0,1);}
;}