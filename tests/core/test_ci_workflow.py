from __future__ import annotations

import re
from pathlib import Path


def test_ci_workflow_referenced_test_files_exist() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    referenced_paths = {
        Path(match.group(0).replace("\\", "/"))
        for match in re.finditer(r"tests[\\/][^\"'\s]+\.py", workflow_text)
    }

    missing_paths = sorted(
        str(path).replace("\\", "/") for path in referenced_paths if not path.exists()
    )

    assert missing_paths == []
