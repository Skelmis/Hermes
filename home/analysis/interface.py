import abc

from home.tables import Vulnerability, Project, Scan


class AnalysisInterface(abc.ABC):
    def __init__(self, project: Project):
        self.project: Project = project

    @classmethod
    @property
    @abc.abstractmethod
    def id(cls) -> str:
        raise NotImplementedError

    @classmethod
    @property
    @abc.abstractmethod
    def language(cls) -> str:
        raise NotImplementedError

    @classmethod
    @property
    @abc.abstractmethod
    def name(cls) -> str:
        raise NotImplementedError

    @classmethod
    @property
    @abc.abstractmethod
    def short_description(cls) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def generate_command(self) -> list[str]:
        """Generate the command to run on the os"""
        raise NotImplementedError

    @abc.abstractmethod
    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        """Run a scan using the tooling and generate a list of vulnerabilities"""
        raise NotImplementedError
