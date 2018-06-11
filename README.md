# PySPPLCompiler
_A simple compiler to create graphical models out of a subset of Python code._ 

This compiler is part of the [Pyfo](https://github.com/bradleygramhansen/pyfo)-project.
As the compiler here provides only the frontend to compile a probabilistic program 
to a graphical model, you might want to use it together a backend to do the actual 
inference.


## Warning

The current project has been used in some limited research projects, but has not yet
been extensively tested. It might not be ready for full production use, i.e. expect
some parts to be still missing, especially in corner cases.

## Installation

```python
git clone https://github.com/bradleygramhansen/PySPPL.git
cd PySPPL
pip install .
```

## Basic Usage

The project requires at least Python 3.4, and has been tested mostly under 
Python 3.6.

In order to compile a model from a program (either Python- or Clojure-based), import
the package and use `compile_model()` or `compile_model_from_file()`, respectively.
The returned object is an instance of the `Model`-class, containing the graphical
model, as well as methods for sampling and computing probabilities according to the
model (see below).

```python
from pyppl import compile_model

my_program = """
x1 = sample(normal(0, 2))
x2 = sample(normal(0, 4))
if x1 > 0:
observe(normal(x2, 1), 1)
else:
observe(normal(-1, 1), 1)
"""

model = compile_model(my_program)
print(model)
```
If you have the packages `networkx`, `matplotlib`, and, ideally, `graphviz` 
installed on your system, you can easily get a picture of the graph displayed:
```python
model.display_graph()
```

#### Examples

Further examples of input programs can be found in the 
[`examples`](examples)-folder. You may want to use `compile_model_from_file()`
to compile them directly to a model, i. e.:
```python
from pyppl import compile_model_from_file

model = compile_model_from_file("examples/my_example.py")
print(model)
```
See [run_example.py](run_example.py).


#### Function `compile_model(source, *, language, namespace)`

Takes a program as input, compiles the entire program, produces a Model-class and 
then returns an instance of this class. The input program is provided as a string 
and can be based on Python, Clojure, or basically any language for which there is a 
frontend (function `get_supported_languages()`). If the language is not specified, 
the system tries to detect the language from the the first characters in the 
provided input.

The compiler transforms the provided model into a graphical model and creates a 
`Model`-class, which is based on `base_model` (see module 
[`ppl_base_model.py`](pyppl/ppl_base_model.py)). 
The last step of compilation consists in creating an instance of this Model, which 
is then returned as `model`-object.

The returned model contains, among other field, lists of the vertices (random 
variables) and arcs (edges between the vertices) of the graphical model as 
specified by the input program. Moreover, the methods `gen_prior_samples()` and 
`gen_log_pdf(state)` can be used to sample for the graphical model (returned as a 
'state' dictionary mapping the vertex names to their respective values), and to 
compute the log probability of a given 'state' (mapping of values for each vertex), 
respectively.


#### Input Languages

The system currently supports the following languages as input:
- Python
- Clojure


#### Namespace

During the compilation process, the names of almost all variables are changed, and 
the compilation relies on heavy inlining, eliminating a lot of names. Your input 
language or DSL, however, might contain predefined names, which should either 
remain unaltered, or be mapped to a specific name of function in the output program. 
As an example, you might want to provide a function `select(...)`, which should be 
mapped to `dist.categorical(...)` during compilation. In order to achieve this, 
provide a `namespace` argument to the compile-function like:
```
compile_model(..., namespace = {'select': 'dist.categorical'})
```
If a name should remain unaltered altogether, use `{'name': 'name'}`.


## The Model Class

The model-class provides a set of methods, of which the most important ones are
described here. More information can be found in the modules
[ppl_base_model.py](pyppl/ppl_base_model.py) and
[ppl_graph_codegen.py](pyppl/backend/ppl_graph_codegen.py), respectively.

**`get_vertices() -> Set[Vertex]`**  
Returns a set of all the vertices/random variables in the model. The elements
of the set are instances of the `Vertex`-class 
(see [graphs.py](pyppl/graphs.py)).

**`get_vertices_names() -> List[str]`**  
Returns a list of the names of the vertices (cf. `get_vertices()`above).

**`get_arcs() -> Set[Tuple[Vertex, Vertex]]`**  
Returns a set of all arcs/edges between vertices in the model. Each arc is
given as a tuple leading from one vertex to another.

**`get_arcs_names() -> List[Tuple[str, str]]`**  
Return a list of the arcs/edges between vertices, where each arc is given as
a tuple of two names (cf. `get_vertices_names()` and `get_arcs()`).

**`gen_prior_samples() -> Dict[str, Any]`**  
Samples from the graphical model and returns a dictionary that provides a
value for each vertex/random variable in the model. The returned dictionary
might contain additional values beside the random variables, and it can be 
used as input `state` in `gen_log_pdf()`.

**`gen_log_pdf(state: Dict[str, Any]) -> float`**  
The `state` argument must be a dictionary that provides values for each 
random variable in the graphical model (see `gen_prior_samples()`). The
function then computes the log probability of the given mapping of values.

**`get_conditions() -> Set[Condition]`**  
Returns a set of all conditions used in the graphical model, where each element
is an instance of the `ConditionNode`-class (see [graphs.py](pyppl/graphs.py)).


## The Graph

The graphical model is represented by a graph comprising vertices (standing for
sampled values and observations) and arcs (directed edges from one vertex to 
another). The vertices are instances of class `Vertex` (to be found in 
[graphs.py](pyppl/graphs.py)).

The basic graphical model is adorned with additional auxiliary nodes that are not
strictly part of the graphical model. On the one hand, there are `ConditionNode`s,
representing conditions inside the probabilistic program. On the other hand, a
`DataNode` might contain some static data in form of a list. The latter are simply
an optimisation to avoid repetitively putting large lists/data-sets into the 
generated code (consider, e. g., a large list `x` with accesses like `x[i]`,
`x[j-1]` etc. sprinkled through the program. According to its inlining policy,
the compiler would rewrite those accesses to something `[1, 2, 3][i]`, which does
not make sense if the list is large).

The conditions associated with a specific vertex can be accessed through its field
`condition_nodes`, which is a set of all conditions directly used for this vertex.

Each node (both vertices and conditions) have the fields `name: str` and
`ancestors: Set[Node]`, the latter being the set of parents, this node directly
depends on. The arcs/edges are not stored separately, but expressed through the
`ancestors`-fields.


#### Vertices

Vertices play the crucial and central role in the graphical model. Each vertex represents either the sampling from
a distribution, or the observation of such a sampled value.

You can get the entire graphical model by taking the set of vertices and their `ancestors`-fields, containing all
vertices, upon which this vertex depends. However, there is a plethora of additional fields, providing information
about the node and its relationship and status.

**`name`**  
The generated name of the vertex. See also: `original_name`.

**`original_name`**  
In contrast to the `name`-field, this field either contains the name attributed to this value in the original
code, or `None`.

**`ancestors`**  
The set of all parent vertices. This contains only the ancestors, which are in direct line, and not the parents
of parents. Use the `get_all_ancestors()`-method to retrieve a full list of all ancestors (including parents of
parents of parents of ...).

**`dist_ancestors`**  
The set of ancestors used for the distribution/sampling, without those used inside the conditions.

**`cond_ancestors`**  
The set of ancestors, which are linked through conditionals.

**`distribution_name`**  
The name of the distribution, such as `Normal` or `Gamma`.

**`distribution_type`**  
Either `"continuous"` or `"discrete"`. You will usually query this field using one of the properties
`is_continuous` or `is_discrete`.

**`distribution_arguments`**  
A dictionary that maps each of the parameters of the distribution used to a string
representing the Python code for its argument. For the _Normal_-distribution with
the parameters `loc` and `scale`, for instance, you might get something like:
`{'loc': "state['x1'] + 3", 'scale': 'math.sqrt(2)'}`.

The individual arguments can also be accessed by position through the field
`distribution_args`, which is a list of strings.

**`observation`**  
The observation as a string containing Python-code.

**`conditions`**  
The set of all conditions under which this vertex is evaluated. Each item in the set is actually a tuple of
a `ConditionNode` and a boolean value, to which the condition should evaluate. Note that the conditions are
not owned by a vertex, but might be shared across several vertices.

**`dependent_conditions`**  
The set of all conditions that depend on this vertex. In other words, all conditions which contain this
vertex in their `get_all_ancestors`-set.

**`sample_size`**  
The dimension of the samples drawn from this distribution.


## Basic Structure of the Compiler

The compiler comprises three major parts:

- A **Frontend** (i.e. [Python](pyppl/fe_python) or [Clojure](pyppl/fe_clojure)) is
responsible for taking a source program (as a string) and to generate an
[_Abstract Syntax Tree_ (AST)](pyppl/ppl_ast.py).
- Several [**Transformations**](pyppl/transforms) use techniques such as inlining,
loop unrolling, and variable renaming to simplify the input program. The objective
of these transformations is to simplify the program so as to extract the graphical
model, not to optimise the code computationally.
- The [**Backend**](pyppl/backend) takes the simplified AST, and generates the code
for the `Model`-class. This code is assembled to a module, so that various imports
can be added, and compiled by Python (using the builtin `compile`-function). The
last step includes creating a new instance of this `Model`-class and adding some
additional information about the graph to this instance.


#### Objective

As input, we have a probabilistic program as a description of the model. In order to
perform further analysis as well as inference, this probabilistic program needs to be
transformed into a graph, where each node/vertex represents either a `sample`- or
an `observe`-statement.

Hence, the objective of the compiler is to rewrite the given probabilistic program so 
that is basically just a linear set of assignments of random variables, i. e.:
```python
x1 = sample(...)
x2 = sample(...)
x3 = sample(...)
observe(..., ...)
```
Each of these `sample`- or `observe`-statements could, of course, depend on any
previously sampled value, leading to the graphical structure of dependencies. But
once we have obtained this simplified form, it is rather easy to extract all vertices
from, and transform the given program into the graphical model.

In addition to these statements, the compiler also supports conditionals, so that
an `observe`-statement, for instance, might actually have a guard:
```python
cond3 = x1 > 0
observe(..., ...) if cond3 else None
observe(..., ...) if not cond3 else None
```


#### Method

To reliably extract the vertices and edges of the graphical model from the
probabilistic model, the compiler needs to make sure of two things. First, it must
make sure that each `sample`- or `observe`-statement is called exactly once (i.e.,
a given statement is not called repeatedly inside a loop, say), so that the correct
number of vertices is extracted from the program. Second, it must make sure the
dependencies between the vertices is expressed correctly.

When an interpreter executes a program, it actually executes one line after another,
possibly jumping forth and back, and thereby executing some lines several times. Our
compiler tries to mimic this behaviour, and records each line as it is executed - 
where a line in the code might actually end up several times in the recording due 
to loops, of course. The result is then a sequence of lines, where loops that repeat
a piece of code, are replaced by the effective repetition of the code lines. Take,
for instance, the following trivial example:
```python
a = 3
for i in range(a):
y = i*i
print(y)
```
The interpreter will execute lines 3 and 4 a total of three times. Hence, our 
compiler should transform this piece of code to:
```python
a = 3
y = 0*0
print(y)
y = 1*1
print(y)
y = 2*2
print(y)
```
In this simple case, it is easy to see that `i` takes on the values `0` to `2`. But
what happens if we cannot easily deduce the exact values `i` takes on? Well, for 
starters, we always need to know _the exact number of iterations_, otherwise there
is nothing we can reliably do. But the values of `i` might come from some yet
unknown list `b`. This is then expressed as:
```python
a = 3
i = b[0]
y = i*i
print(y)
i = b[1]
y = i*i
print(y)
i = b[2]
y = i*i
print(y)
```

Loops are not the only case the compiler must take care of. A few examples of what
the compiler must look out for...

- `a = sample(normal(4, sample(uniform(1.0, 4.0))))` needs to be rewritten into two
separate `sample`-statements: `x1 = sample(uniform(1.0, 4.0))` and
`x2 = sample(normal(4, x1))` (note that the variable names inside the original
program have no influence on the naming of the vertices).

- `for y in [2, 4, 3.5, 5]: observe(normal(4, 1), y)` needs to be unrolled, since
there are actually four separate `observe`-statements involved here, each of which
represents its own vertex or node in the graphical model.

Note that this unrolling can only be done if at least the length of the list is
known to the compiler. Otherwise, the linearisation cannot be done properly. On
the other hand, we do not strictly need to unroll every loop - only those that 
have `sample`- or `observe`-statements inside the body.

- When a function contains a `sample`- or `observe`-statement, like, say, 
`def foo(a, b): return sample(normal(a+b, 1.0))`, we need to inline the function
each time it is called, since each call actually stands for a sampling, which is
expressed as a separate vertex/node in the graph.


In order to keep the compiler's code manageable, the different transformations have
been mostly split into various passes. Each transformation is thereby implemented
using the [_visitor_-pattern](https://en.wikipedia.org/wiki/Visitor_pattern).



## License

This project is released under the _GNU GPL 3_-license. 
See [LICENSE](LICENSE).


## Contributors
- [Tobias Kohn](https://tobiaskohn.ch)
- [Bradley Gram-Hansen](http://www.robots.ox.ac.uk/~bradley/)

