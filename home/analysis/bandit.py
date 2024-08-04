from home.analysis import AnalysisInterface
from home.tables import Vulnerability, Project


class Bandit(AnalysisInterface):
    id = "bandit"
    name = "Bandit (Python)"
    short_description = "Security oriented static analyser for python code."

    def scan(self) -> list[Vulnerability]:
        pass
