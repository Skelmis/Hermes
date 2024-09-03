import subprocess
from typing import TypedDict

import orjson

from home.analysis import AnalysisInterface
from home.tables import Scan, Vulnerability


class GSIssuse(TypedDict):
    severity: str
    confidence: str
    details: str
    file: str
    code: str
    line: str


class GoSecResult(TypedDict):
    Issues: list[GSIssuse]


class GoSec(AnalysisInterface):
    id = "gosec"
    name = "GoSec"
    language = "Go"
    short_description = "Inspects source code for security problems by scanning the Go AST and SSA code representation."

    def generate_command(self) -> list[str]:
        return [
            "gosec",
            "-fmt",
            "json",
            "-quiet",
            f"{self.project.scanner_path}/./...",
        ]

    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        scan = await self.get_scan(scan)
        result_str = await self.run_scanner()
        result: GoSecResult = orjson.loads(result_str)
        vulns: list[Vulnerability] = []
        for issue in result["Issues"]:
            vuln = Vulnerability(
                scan=scan,
                project=self.project,
                title=issue["details"],
                description=issue["details"],
                code_file=self.project.normalize_finding_path(issue["file"]),
                code_line=issue["line"],
                code_context=issue["code"],
                severity=issue["severity"],
                confidence=issue["confidence"],
                found_by=self.id,
                extra_metadata=issue,
            )
            await vuln.save()
            vulns.append(vuln)

        return vulns
