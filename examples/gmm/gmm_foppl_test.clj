 (defn sample-likelihoods [_ likes]
      (let [precision (sample (gamma 1.0 1.0))
            mean (sample (normal 0.0 precision))
            sigma (/ precision)]
        (conj likes
              (normal mean sigma))))

    (defn sample-components [_ zs prior]
      (let [z (sample prior)]
        (conj zs z)))

    (defn observe-data [n _ ys zs likes]
      (let [y (nth ys n)
            z (nth zs n)]
        (observe (nth likes z) y)
        nil))

    (let [ys (vector 1.1 2.1 2.0 1.9 0.0 -0.1 -0.05)
          z-prior (binomial
                    (sample (dirichlet (vector 1.0 1.0 1.0))))
          zs (loop 7 (vector) sample-components z-prior)
          likes (loop 3 (vector) sample-likelihoods)]
      (loop 7 nil observe-data ys zs likes)
      zs)