import sys
import warnings
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1].parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Passlib still imports the deprecated stdlib ``crypt`` module when available.
# Filter the warning globally so it doesn't pollute the test output.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"passlib\.utils.*",
)

