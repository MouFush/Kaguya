import sys
print("Python path:")
for p in sys.path:
    print(f"  {p}")

print("\n检查tensorflow...")
try:
    import tensorflow as tf
    print(f"TensorFlow found: {tf.__file__}")
except ImportError as e:
    print(f"TensorFlow not found: {e}")

print("\n检查transformers...")
from transformers.utils.import_utils import is_tf_available
print(f"is_tf_available(): {is_tf_available()}")
