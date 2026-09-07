from abc import ABC, abstractmethod

from ephys_link.models import ManipulatorStateResponse


class BaseBinding(ABC):
    @abstractmethod
    def state(self) -> ManipulatorStateResponse:
        pass
