import abc
import subprocess

import anyio.to_process

from home.tables import Vulnerability, Project, Scan


class AnalysisInterface(abc.ABC):
    def __init__(self, project: Project):
        self.project: Project = project

    async def get_scan(self, scan: Scan | None) -> Scan:
        if scan is None:
            scan = Scan(
                project=self.project,
                number=await Scan.get_next_number(self.project),
            )
            await scan.save()

        return scan

    async def run_command(self, command: list[str]) -> bytes:
        try:
            result_str = await anyio.run_process(command)
            result_str = result_str.stdout
        except subprocess.CalledProcessError as e:
            if e.returncode != 1:
                print(e.output)
                raise e
            # Lol this is likely fine
            result_str = e.stdout
        return result_str

    async def run_scanner(self) -> bytes:
        return await self.run_command(self.generate_command())

    async def set_version_string(self, scan: Scan) -> None:
        scanner_version = await self.get_version_string()
        scan.scanner_versions_used.append(scanner_version)
        await scan.save()

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
    def generate_command(self) -> list[str]:
        """Generate the command to run on the os"""
        raise NotImplementedError

    @abc.abstractmethod
    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        """Run a scan using the tooling and generate a list of vulnerabilities"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_version_string(self) -> str:
        """Return the current version of the scanner"""
        raise NotImplementedError
