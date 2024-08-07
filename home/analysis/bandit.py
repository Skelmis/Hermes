import subprocess
from typing import TypedDict, cast

import orjson

from home.analysis import AnalysisInterface
from home.tables import Vulnerability, Project, Scan


class BanditError(TypedDict):
    filename: str
    reason: str


class IssueCWE(TypedDict):
    id: int
    link: str


class BanditResult(TypedDict):
    test_id: str
    test_name: str
    more_info: str
    line_range: list[int]
    line_number: int
    issue_text: str
    issue_cwe: IssueCWE
    issue_severity: str
    issue_confidence: str
    code: str
    filename: str


# Example metrics
"""
"./suggestions/__init__.py": {
      "CONFIDENCE.HIGH": 0,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 0,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 9,
      "nosec": 0,
      "skipped_tests": 0
    },
"""


class BanditOutput(TypedDict):
    generated_at: str  # 2024-08-04T04:18:42Z
    errors: list[BanditError]
    metrics: dict[str, dict[str, int]]
    results: list[BanditResult]


class Bandit(AnalysisInterface):
    id = "bandit"
    name = "Bandit"
    language = "Python"
    short_description = "Security oriented static analyser for python code."

    async def scan(self) -> list[Vulnerability]:
        scan = Scan(
            project=self.project,
            number=await Scan.get_next_number(self.project),
        )
        await scan.save()
        command: list[str] = [
            "bandit",
            "-q",  # Only output result json
            "-f",
            "json",
            "-r",
            self.project.scanner_path,
        ]
        try:
            result_str: bytes = subprocess.check_output(
                command,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            if e.returncode != 1:
                raise e
            # Lol this is likely fine
            result_str = e.stdout
        result: BanditOutput = orjson.loads(result_str)

        vulns: list[Vulnerability] = []
        for issue in result["results"]:
            issue = cast(BanditResult, issue)
            vuln = Vulnerability(
                scan=scan,
                project=self.project,
                title=f"{issue['test_id']}:{issue['test_name']}",
                description=issue["issue_text"],
                code_file=self.project.normalize_finding_path(issue["filename"]),
                code_line=issue["line_number"],
                code_context=issue["code"],
                severity=issue["issue_severity"],
                confidence=issue["issue_confidence"],
                found_by=self.id,
            )
            await vuln.save()
            vulns.append(vuln)

        return vulns
