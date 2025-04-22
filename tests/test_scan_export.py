import datetime

from dateutil.tz import tzutc
from freezegun import freeze_time
from piccolo.apps.user.tables import BaseUser

from home.tables import Vulnerability, Project, Scan


@freeze_time("2025-01-10")
async def test_scan_as_json():
    user_1 = BaseUser(username="ethan", password="password")
    await user_1.save()
    project_1 = Project(owner=user_1, title="Project", code_scanners=["bandit"])
    await project_1.save()
    scan_1 = Scan(project=project_1, number=1, scanner_versions_used=["Bandit 1.2.3"])
    await scan_1.save()
    vuln_1 = Vulnerability(scan=scan_1, project=project_1, title="Vuln 1")
    vuln_2 = Vulnerability(scan=scan_1, project=project_1, title="Vuln 2")
    await vuln_1.save()
    await vuln_2.save()

    expected = {
        "archive_created_at": datetime.datetime(2025, 1, 10, 0, 0, tzinfo=tzutc()),
        "archive_creator": {
            "email": "",
            "first_name": "",
            "last_name": "",
            "username": "ethan",
        },
        "scan": {
            "id": scan_1.id,
            "project": {
                "code_scanners": ["bandit"],
                "created_at": datetime.datetime(
                    2025, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                ),
                "description": "",
                "id": project_1.id,
                "is_git_based": False,
                "is_public": False,
                "owner": {
                    "email": "",
                    "first_name": "",
                    "last_name": "",
                    "username": "ethan",
                },
                "title": "Project",
            },
            "scan_number": 1,
            "scanned_at": datetime.datetime(
                2025, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "scanner_versions_used": ["Bandit 1.2.3"],
            "vulnerabilities": [
                {
                    "code_context": "",
                    "code_file": "",
                    "code_line": "",
                    "confidence": "",
                    "created_at": datetime.datetime(
                        2025, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "description": "",
                    "exploitability": "Unknown",
                    "extra_metadata": "{}",
                    "found_by": "Unknown",
                    "id": vuln_1.id,
                    "impact": "",
                    "likelihood": "",
                    "notes": "",
                    "severity": "",
                    "state": "New",
                    "title": "Vuln 1",
                },
                {
                    "code_context": "",
                    "code_file": "",
                    "code_line": "",
                    "confidence": "",
                    "created_at": datetime.datetime(
                        2025, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "description": "",
                    "exploitability": "Unknown",
                    "extra_metadata": "{}",
                    "found_by": "Unknown",
                    "id": vuln_2.id,
                    "impact": "",
                    "likelihood": "",
                    "notes": "",
                    "severity": "",
                    "state": "New",
                    "title": "Vuln 2",
                },
            ],
        },
    }
    data = await scan_1.export_as_json(user_1)
    assert data == expected
