(def latent-dim 2)

(def hidden-dim 10)

(def output-dim 5)

;(require '[clojure.core.matrix :as mat :refer [mmul add mul div sub]])

(defn append-gaussian [_ v]
  (conj v (sample (normal 0.0 1.0))))

(defn make-latent-vector [_]
  (loop latent-dim [] append-gaussian))

(defn make-hidden-vector [_]
  (loop hidden-dim [] append-gaussian))

(defn make-output-vector [_]

  (loop output-dim [] append-gaussian))

(defn append-latent-vector [_ M]
  (conj M (make-latent-vector)))

(defn append-hidden-vector [_ M]
  (conj M (make-hidden-vector)))

(defn append-output-vector [_ M]
  (conj M (make-output-vector)))

(defn relu [v]
  (mul (mat/ge v 0.0) v))

;(defn sigmoid [v]
;  (div 1.0 (add 1.0 (mat/exp (sub 0.0 v)))))
;
;(defn append-flip [i v p]
;  (conj v (sample (flip (nth p i)))))
;  (matrix/mul (matrix/ge v 0.0) v))

(defn sigmoid [v]
  (matrix/div 1.0 (matrix/add 1.0 (matrix/exp (matrix/sub 0.0 v)))))

(defn append-flip [i v p]
  (conj v (sample (binomial (nth p i)))))


(let [z (make-latent-vector)

      ;; first: hidden layer
      W (loop hidden-dim [] append-latent-vector)
      b (make-hidden-vector)
;      h (relu (add (mmul W z) b))
      h (relu (matrix/add (matrix/mmul W z) b))

      ;; output layer
      V (loop output-dim [] append-hidden-vector)
      c (make-output-vector)]
;  (loop output-dim [] append-flip (sigmoid (add (mmul V h) c))))
  (loop output-dim [] append-flip (sigmoid (matrix/add (matrix/mmul V h) c))))
