# Setup the FOPPL-compiler and auto-importer:
from foppl import Options, imports
# Print additional information:
Options.debug = True

# Import and compile the model:
import onegauss as foppl_model

# Print out the entire model:
print(foppl_model.model)

print("=" * 30)
print("CODE")
print(foppl_model.model.gen_prior_samples_code)
print("-" * 30)
print(foppl_model.model.gen_pdf_code)
print("-" * 30)

# A sample run with the model:
print("=" * 30)
state = foppl_model.model.gen_prior_samples()
print("-" * 30)
for i in range(10):
    state['log_pdf'] = 0.0
    pdf = foppl_model.model.gen_pdf(state)
print("Result: {}\nLog-PDF: {}".format(foppl_model.model.get_result(state), pdf))

print("=" * 30)
state = foppl_model.model.transform_state(state, samples_only=True)
for key in sorted(state.keys()):
    print("{}  -> {}".format(key, state[key]))

foppl_model.model.display_graph()