from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.services.stack.stack_detector import ProjectStackMetadata


class BaseEcosystemAdapter(ABC):
    """
    Abstract ecosystem adapter defining test discovery and diagnostic execution contracts.
    """

    @abstractmethod
    def can_handle(self, metadata: ProjectStackMetadata) -> bool:
        """Return True if this adapter is suited for the detected stack."""
        pass

    @abstractmethod
    def discover_tests(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata
    ) -> Dict[str, Any]:
        """Discover existing tests, frameworks, and suggested test commands."""
        pass

    @abstractmethod
    def execute_diagnostics(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata,
        test_command: Optional[str] = None,
        test_path: Optional[str] = None,
        timeout_seconds: int = 25
    ) -> Dict[str, Any]:
        """
        Execute diagnostics/tests in the workspace.
        Must report real subprocess results or clean prerequisite limitations.
        Must NEVER falsify test outcomes.
        """
        pass
