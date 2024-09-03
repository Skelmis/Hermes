import subprocess
from typing import TypedDict, cast

import orjson

from home.analysis import AnalysisInterface
from home.tables import Vulnerability, Scan


class SemgrepStart(TypedDict):
    col: int
    line: int
    offset: int


class SemgrepMetadata(TypedDict):
    confidence: str
    impact: str
    likelihood: str
    cwe: list[str]


class SemgrepResultExtra(TypedDict):
    lines: str
    message: str
    severity: str
    metadata: SemgrepMetadata


class SemgrepResult(TypedDict):
    check_id: str
    path: str
    extra: SemgrepResultExtra
    start: SemgrepStart


class SemgrepOutput(TypedDict):
    results: list[SemgrepResult]


# noinspection DuplicatedCode
class Semgrep(AnalysisInterface):
    id = "semgrep"
    name = "Semgrep"
    language = "Generic"
    short_description = "A generic code scanner for all languages."

    def generate_command(self) -> list[str]:
        return [
            "semgrep",
            "scan",
            "--json",
            "-q",
            "--no-git-ignore",
            "--config",
            "auto",
            self.project.scanner_path,
        ]

    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        scan = await self.get_scan(scan)
        result_str = await self.run_scanner()
        result: SemgrepOutput = orjson.loads(result_str)
        vulns: list[Vulnerability] = []
        for issue in result["results"]:
            issue = cast(SemgrepResult, issue)
            extra = cast(SemgrepResultExtra, issue["extra"])
            metadata = cast(SemgrepMetadata, extra["metadata"])
            vuln = Vulnerability(
                scan=scan,
                project=self.project,
                title=issue["check_id"],
                description=issue["extra"]["message"],
                code_file=self.project.normalize_finding_path(issue["path"]),
                code_line=str(issue["start"]["line"]),
                code_context=extra["lines"],
                severity=extra["severity"],
                confidence=metadata["confidence"],
                impact=metadata["impact"],
                likelihood=metadata["likelihood"],
                found_by=self.id,
                extra_metadata=issue,
            )
            await vuln.save()
            vulns.append(vuln)

        return vulns
