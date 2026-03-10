"""
PDAA Git Sync — Git-backed canonical store for demand signals.

Signals are stored as JSON files in a Git repo:
  <PDAA_GIT_REPO_PATH>/signals/<signal_id>.json

If PDAA_GIT_REPO_PATH is not set, falls back to a local directory
at <project_root>/pdaa_data/signals/.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from .models import DemandSignal

log = logging.getLogger("pdaa.git_sync")

_FALLBACK_DIR = Path(__file__).parent.parent / "pdaa_data" / "signals"


class GitSyncManager:
    def __init__(self):
        repo_path = os.environ.get("PDAA_GIT_REPO_PATH", "")
        if repo_path:
            self.signals_dir = Path(repo_path) / "signals"
        else:
            self.signals_dir = _FALLBACK_DIR
        self.signals_dir.mkdir(parents=True, exist_ok=True)
        self.use_git = bool(repo_path)

    def _signal_path(self, signal_id: str) -> Path:
        return self.signals_dir / f"{signal_id}.json"

    def save_signal(self, signal: DemandSignal) -> Path:
        """Write signal JSON to disk and optionally git commit."""
        path = self._signal_path(signal.id)
        path.write_text(json.dumps(signal.to_dict(), indent=2))

        if self.use_git:
            self._git_commit(path, f"Update signal: {signal.title}")

        return path

    def load_signal(self, signal_id: str) -> Optional[DemandSignal]:
        path = self._signal_path(signal_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return DemandSignal.from_dict(data)

    def load_all_signals(self) -> List[DemandSignal]:
        signals = []
        if not self.signals_dir.exists():
            return signals
        for path in sorted(self.signals_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                signals.append(DemandSignal.from_dict(data))
            except Exception as e:
                log.warning(f"Failed to load signal {path.name}: {e}")
        return signals

    def _git_commit(self, path: Path, message: str):
        """Stage and commit a single file. Best-effort, never raises."""
        try:
            cwd = str(self.signals_dir.parent)
            subprocess.run(["git", "add", str(path)], cwd=cwd, capture_output=True, timeout=10)
            subprocess.run(
                ["git", "commit", "-m", message, "--", str(path)],
                cwd=cwd, capture_output=True, timeout=10,
            )
        except Exception as e:
            log.debug(f"Git commit skipped: {e}")
