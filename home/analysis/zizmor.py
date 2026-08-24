import io
import linecache
from typing import TypedDict

import orjson

from home.analysis import AnalysisInterface
from home.tables import Scan, Vulnerability


class Determinations(TypedDict):
    confidence: str
    severity: str
    persona: str


class Local(TypedDict):
    verbatim_path: str


class Key(TypedDict):
    Local: Local


class RouteItem1(TypedDict):
    Key: str


class RouteItem2(TypedDict):
    index: str


class Route(TypedDict):
    route: list[RouteItem1 | RouteItem2]


class Symbolic(TypedDict):
    key: Key
    annotation: str
    route: Route


class Start(TypedDict):
    row: int


class End(TypedDict):
    row: int


class ConcreateLocation(TypedDict):
    start_point: Start
    end_point: End


class Concrete(TypedDict):
    feature: str  # Code
    location: ConcreateLocation


class Locations(TypedDict):
    symbolic: Symbolic
    concrete: Concrete


class Fixes(TypedDict):
    title: str
    key: Key
    disposition: str


class ZizmorResult(TypedDict):
    ident: str
    desc: str
    url: str
    determinations: Determinations
    ignored: str
    locations: list[Locations]


class Zizmor(AnalysisInterface):
    id = "zizmor"
    name = "Zizmor"
    language = "CI/CD"
    short_description = "It can find and fix security issues in common CI/CD setups, including GitHub Actions, Dependabot, and pre-commit."

    def generate_command(self) -> list[str]:
        return [
            "uv",
            "run",
            "zizmor",
            "--format=json",
            "--quiet",
            "--no-ignores",
            "--no-progress",
            "--offline",
            "--no-exit-codes",
            f"{self.project.scanner_path}",
        ]

    async def get_version_string(self) -> str:
        result = await self.run_command(["uv", "run", "zizmor", "--version"])
        result = result.decode().split("\n")[0].split(" ")[1]
        return f"{self.name} {result}"

    async def scan(self, scan: Scan | None = None) -> list[Vulnerability]:
        scan = await self.get_scan(scan)
        await self.set_version_string(scan)
        result_str = await self.run_scanner()
        results: list[ZizmorResult] = orjson.loads(result_str)
        vulns: list[Vulnerability] = []

        for issue in results:
            for entry in issue["locations"]:
                description = io.StringIO()
                description.write(issue["desc"].capitalize())
                description.write("\n")
                description.write(entry["symbolic"]["annotation"])
                description.write("\n")
                description.write(f"Read more at {issue['url']}")
                code = io.StringIO()

                def add_to_code(line_no: int) -> None:
                    # Function is safe to call without checking the line exists
                    line = linecache.getline(
                        entry["symbolic"]["key"]["Local"]["verbatim_path"], line_no
                    )
                    if not line:
                        return

                    code.write(f"{line_no} {line}")

                code_line = entry["concrete"]["location"]["start_point"]["row"]
                end_line = entry["concrete"]["location"]["end_point"]["row"]
                add_to_code(code_line - 1)
                add_to_code(code_line)
                add_to_code(code_line + 1)
                add_to_code(code_line + 2)
                add_to_code(code_line + 3)
                add_to_code(code_line + 4)
                add_to_code(code_line + 5)
                affected_code_line = (
                    code_line if code_line == end_line else f"{code_line}-{end_line}"
                )

                vuln = Vulnerability(
                    scan=scan,
                    project=self.project,
                    title=issue["desc"],
                    description=description.getvalue(),
                    code_file=self.project.normalize_finding_path(
                        entry["symbolic"]["key"]["Local"]["verbatim_path"]
                    ),
                    code_line=str(affected_code_line),
                    code_context=code.getvalue(),
                    severity=issue["determinations"]["severity"],
                    confidence=issue["determinations"]["confidence"],
                    found_by=self.id,
                    extra_metadata=issue,
                )
                await vuln.save()
                vulns.append(vuln)

        return vulns
