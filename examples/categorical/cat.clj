(let[z (sample (categorical [0.7 0.15 0.15]))
     z1 (sample (categorical [0.1 0.5 0.4]))
     z2 (sample (categorical [0.2 0.2 0.6]))]
  z z1 z2)
;(let[z1 (sample (categorical [[0.1, 0.5, 0.4],
;                              [0.2, 0.2, 0.6]]))]
;  z1)
;
