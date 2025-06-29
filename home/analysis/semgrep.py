import io
import linecache
from pathlib import Path
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
    language = "Generic (Non-Commercial)"
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

    async def get_version_string(self) -> str:
        result = await self.run_command(["semgrep", "--version"])
        result = result.decode().split("\n")[0]
        return f"{self.name} {result}"

    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        scan = await self.get_scan(scan)
        await self.set_version_string(scan)
        result_str = await self.run_scanner()
        result: SemgrepOutput = orjson.loads(result_str)
        vulns: list[Vulnerability] = []
        for issue in result["results"]:
            issue = cast(SemgrepResult, issue)
            extra = cast(SemgrepResultExtra, issue["extra"])
            metadata = cast(SemgrepMetadata, extra["metadata"])

            # Semgrep hides this behind login
            code = io.StringIO()

            def add_to_code(line_no: int) -> None:
                # Function is safe to call without checking the line exists
                line = linecache.getline(issue["path"], line_no)
                if not line:
                    return

                code.write(f"{line_no} {line}")

            add_to_code(issue["start"]["line"] - 2)
            add_to_code(issue["start"]["line"] - 1)
            add_to_code(issue["start"]["line"])
            add_to_code(issue["start"]["line"] + 1)
            add_to_code(issue["start"]["line"] + 2)
            add_to_code(issue["start"]["line"] + 3)
            add_to_code(issue["start"]["line"] + 4)

            vuln = Vulnerability(
                scan=scan,
                project=self.project,
                title=issue["check_id"],
                description=issue["extra"]["message"],
                code_file=self.project.normalize_finding_path(issue["path"]),
                code_line=str(issue["start"]["line"]),
                code_context=code.getvalue(),
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
