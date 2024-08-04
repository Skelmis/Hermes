import abc

from home.tables import Vulnerability


class AnalysisInterface(abc.ABCMeta):
    @abc.abstractmethod
    def scan(self) -> list[Vulnerability]:
        """Run a scan using the tooling and generate a list of vulnerabilities"""
        raise NotImplementedError
