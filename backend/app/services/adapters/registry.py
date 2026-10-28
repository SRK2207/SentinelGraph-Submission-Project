from typing import List
from backend.app.services.adapters.base import BaseEcosystemAdapter
from backend.app.services.adapters.gradle_adapter import GradleKotlinAdapter
from backend.app.services.adapters.node_adapter import NodeAdapter
from backend.app.services.adapters.python_adapter import PythonAdapter
from backend.app.services.adapters.generic_adapter import GenericAdapter
from backend.app.services.stack.stack_detector import ProjectStackMetadata


class AdapterRegistry:
    """
    Registry that resolves the appropriate diagnostic and test adapter
    for a given project stack.
    """

    def __init__(self):
        # Order matters: GradleKotlin and Node adapters are checked before Python
        # to ensure Kotlin/Gradle or Node projects with incidental python scripts
        # are never misrouted to pytest.
        self._adapters: List[BaseEcosystemAdapter] = [
            GradleKotlinAdapter(),
            NodeAdapter(),
            PythonAdapter(),
            GenericAdapter()
        ]

    def get_adapter(self, metadata: ProjectStackMetadata) -> BaseEcosystemAdapter:
        for adapter in self._adapters:
            if adapter.can_handle(metadata):
                return adapter
        return self._adapters[-1]


adapter_registry = AdapterRegistry()
