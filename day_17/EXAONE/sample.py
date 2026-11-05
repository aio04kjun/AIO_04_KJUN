import inspect
import transformers
from transformers.masking_utils import create_causal_mask

print("Transformers:", transformers.__version__)
print(inspect.signature(create_causal_mask))