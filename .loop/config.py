"""流水线配置。"""

from pathlib import Path

LOOP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = LOOP_ROOT.parent
PROMPTS_DIR = LOOP_ROOT / "prompts"
BRIDGE_STATE_ROOT = LOOP_ROOT / ".bridge-state"

DEFAULT_MODEL = "composer-2.5"
BRIDGE_LAUNCH_TIMEOUT_SECONDS = 60.0
MAX_EXECUTOR_ROUNDS = 15
MAX_REVIEW_CYCLES = 5
MAX_REDO_CYCLES = 3
