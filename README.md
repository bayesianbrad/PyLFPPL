# PySPPL

**A Framework for First Order Probabilistic Programming Languages**

_This is a work in progress._

## Usage

Write your FOPPL-model and save in a file, say, `my_model.foppl`. The file
should either be in the root folder of your project, or in a folder called
`foppl-src` or `foppl-models`. A simple model might look as follows:
```clojure
(let [x (sample (normal 1.0 5.0))
      y (+ x 1)]
  (observe (normal y 2.0) 7.0)
  y)
```
You will find various models in the `examples`-folder in this project.

Once you have written your FOPPL-model, you can import it as a graphical
model in your Python code like this:

```python
from foppl import imports

# Import your model here:
from my_model import model

state = model.gen_prior_samples()
log_pdf = model.gen_pdf(state)
print(log_pdf)
```

You can get a visual representation of the graphical model if you have
the Python packages `networkx` and `matplotlib` installed (preferably
also `graphviz`).
```python
model.display_graph()
```

The file [example.py](example.py) shows how you might import a FOPPL mode, 
print out the generated graphical model, or generate samples from it. 

## Options

`Options.debug: bool`:  
  When set to `True`, _PyFOPPL_ will print out additional debug information.
  On the one hand, the output of the vertices will include addition
  information. On the other hand, when running `gen_prior_samples()`, or
  `gen_pdf()`, respectively, it will print out the performed computations
  as they happen.
  
`Options.log_file: str`:  
  This lets you specify a possible _log-file_. When given a filename as a
  string, the _graph_ will print out the entire model and the generated
  code for `gen_prior_samples()` as well as `gen_pdf()` to the specified
  logfile.

In order to take effect during the import of any models, the options should
be set before the actual import. You can, later on, deactivate the 
debug-option, if you do not need the runtime-output.
```python
from foppl import Options
Options.debug = True

import my_model  # Import your model here!

Options.debug = False
state = my_model.model.gen_prior_samples()
...
```

## License

This project is released unter the _MIT_-license. 
See [LICENSE](LICENSE).

## Papers
[Discontinuous Hamiltonian Monte Carlo for Probabilistic Programs](https://arxiv.org/abs/1804.03523)

## Contributors

- [Tobias Kohn](https://tobiaskohn.ch)
- [Bradley Gram-Hansen](http://www.robots.ox.ac.uk/~bradley/)
- [Yuan Zhou](https://www.cs.ox.ac.uk/people/yuan.zhou/)
- [Frank Wood](http://www.robots.ox.ac.uk/~fwood/)
- [Honseok Yang](https://sites.google.com/view/hongseokyang/home)

