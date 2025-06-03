import os
from pathlib import Path

from commons import value_to_bool

from home.analysis import AnalysisInterface, Bandit, Semgrep, GoSec, Brakeman

REGISTERED_INTERFACES: dict[str, type[AnalysisInterface]] = {
    Bandit.id: Bandit,
    Semgrep.id: Semgrep,
    GoSec.id: GoSec,
    Brakeman.id: Brakeman,
}
BASE_PROJECT_DIR: Path = Path(os.environ.get("PROJECT_DIR", ".projects"))
BASE_PROJECT_DIR.mkdir(exist_ok=True)  # Ensure it exists


ALLOW_REGISTRATION: bool = value_to_bool(os.environ.get("ALLOW_REGISTRATION", True))
"""Whether users should be allowed to create new accounts."""
