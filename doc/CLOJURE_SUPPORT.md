# Supported Features of Clojure

_This document gives an overview of features from `Clojure`, which are
supported by the compiler._

The compiler is not intended as a fully fledged Clojure-compiler. It
rather provides a basic framework, upon which to build the FOPPL-system.
For a LISP-compiler in Python, consider the 
 [Hy-Language](https://github.com/hylang/hy).
 
Some limitations of the current implementation:

- Macros are not supported.
- Only vectors are supported, but not lists.

## Special Forms and Core Functions

Other forms encountered are considered to be simple function calls.

`(. x y)`  
`(+ x & y)`  
`(- x y)`  
`(-> init & functions)`  
`(->> init & functions)`  
`(* x & y)`  
`(/ x y)`  
`(= x y)`  
`(< x y)`  
`(<= x y)`  
`(> x y)`  
`(>= x y)`  
`(!= x y)`  
`(and x y)`  
`(apply f & args)`  
`(bit-and x y)`  
`(bit-or x y)`  
`(bit-xor x y)`  
`(concat x y)`  
`(cond & clauses)`  
`(conj coll x)`  
`(cons x seq)`  
`(contains? map key)`  
`(dec x)`
  _Translates to: `(- x 1)`_  
`(def name value)`  
`(defn name [& params] body)`  
`(do & stmts)`  
`(doseq [& bindings] body)`  
`(drop n coll)`  
`(first seq)`  
`(fn [& params] body)`  
`(for [& bindings] body)`  
`(get coll n)`  
`(if test expr expr)`  
`(if-not test expr expr)`  
`(inc x)`
  _Translates to: `(+ x 1)`_  
`(last coll)`  
`(let [& bindings] body)`  
`(nth coll x)`
  _Same as `(get coll x)`._  
`(not x)`  
`(not= x y)` _Same as `!=`._  
`(or x y)`  
`(repeat n value)`
`(repeatedly n function)`  
`(require 'name)`  
`(rest coll)`  
`(second coll)`  
`(setv name value)`
 _Variable assignment, Python-style; copied from 'Hy'._  
`(subvec coll start stop)`  
`(take n coll)`  
`(use 'name)`  
`(vector & elems)`  
`(while test & body)`  
`false`  
`nil` _Translates to Python's `None`._  
`true`  

## Probabilistic Programming

There are two further functions, which are supported out of the box:
`(sample dist)` and `(observe dist value)`.
