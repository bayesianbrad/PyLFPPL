(def latent-dim 2)

(def hidden-dim 10)

(def output-dim 5)

(defn append-gaussian [_ v]
  (conj v (sample (normal 0.0 1.0))))

(defn make-latent-vector []
  (loop latent-dim [] append-gaussian))

(defn make-hidden-vector []
  (loop hidden-dim [] append-gaussian))

(defn make-output-vector []
  (loop output-dim [] append-gaussian))

(defn append-latent-vector [_ M]
  (conj M (make-latent-vector)))

(defn append-hidden-vector [_ M]
  (conj M (make-hidden-vector)))

(defn append-output-vector [_ M]
  (conj M (make-output-vector)))

(defn relu [v]
  (matrix/mul (matrix/ge v 0.0) v))

(defn sigmoid [v]
  (matrix/div 1.0 (matrix/add 1.0 (matrix/exp (matrix/sub 0.0 v)))))

(defn append-flip [i v p]
  (conj v (sample (binomial 1 (nth p i)))))

(let [z (make-latent-vector)

      ;; first: hidden layer
      W (loop hidden-dim [] append-latent-vector)
      b (make-hidden-vector)
      h (relu (matrix/add (matrix/mmul W z) b))

      ;; output layer
      V (loop output-dim [] append-hidden-vector)
      c (make-output-vector)]
  (loop output-dim [] append-flip (sigmoid (matrix/add (matrix/mmul V h) c))))