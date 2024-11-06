from typing import TypedDict

import orjson

from home.analysis import AnalysisInterface
from home.tables import Scan, Vulnerability


class Result(TypedDict):
    warning_type: str
    warning_code: int
    message: str
    file: str
    line: int
    link: str
    code: str
    confidence: str
    cwe_id: list[int]
    user_input: str | None  # Where user input goes


class BrakemanOutput(TypedDict):
    warnings: list[Result]
    ignored_warnings: list[Result]


class Brakeman(AnalysisInterface):
    id = "brakeman"
    name = "Brakeman"
    language = "Ruby"
    short_description = "Security oriented static analyser for ruby code."

    def generate_command(self) -> list[str]:
        return [
            "brakeman",
            "-f",
            "json",
            "--no-exit-on-warn",
            "--no-exit-on-error",
            "-A",
            "--force",
            self.project.scanner_path,
        ]

    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        scan = await self.get_scan(scan)
        result_str = await self.run_scanner()
        result: BrakemanOutput = orjson.loads(result_str)

        vulns: list[Vulnerability] = []
        for issue in result["warnings"]:
            vuln = Vulnerability(
                scan=scan,
                project=self.project,
                title=issue["warning_type"],
                description=issue["message"],
                code_file=self.project.normalize_finding_path(issue["file"]),
                code_line=str(issue["line"]),
                code_context=issue["code"],
                confidence=issue["confidence"],
                found_by=self.id,
                extra_metadata=issue,
            )
            await vuln.save()
            vulns.append(vuln)

        for issue in result["ignored_warnings"]:
            vuln = Vulnerability(
                scan=scan,
                project=self.project,
                title=issue["warning_type"],
                description=f"*Brakeman disclosed this as an ignored warning.*\n{issue['message']}",
                code_file=self.project.normalize_finding_path(issue["file"]),
                code_line=str(issue["line"]),
                code_context=issue["code"],
                confidence=issue["confidence"],
                found_by=self.id,
                extra_metadata=issue,
            )
            await vuln.save()
            vulns.append(vuln)

        return vulns
