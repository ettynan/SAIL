
from pathlib import Path

directory = Path("src/components")
source = directory / "UserManagement.test.jsx"
content = source.read_text()

sections = [
    ("UserProfile", "UserProfile.test.jsx"),
    ("PublicProfile", "PublicProfile.test.jsx"),
    ("AdminAccounts", "AdminAccounts.test.jsx"),
]

imports = '''import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

'''

api_functions = {
    "UserProfile": "getOwnProfile, updateOwnProfile",
    "PublicProfile": "getPublicProfile",
    "AdminAccounts": "updateUserStatus",
}

for index, (component, filename) in enumerate(sections):
    marker = f'describe("{component}", () => {{'
    start = content.index(marker)

    if index + 1 < len(sections):
        next_marker = f'describe("{sections[index + 1][0]}", () => {{'
        end = content.index(next_marker)
    else:
        end = len(content)

    # Include the documentation comment immediately preceding each section.
    comment_start = content.rfind("/**", 0, start)
    section = content[comment_start:end].rstrip() + "\n"

    header = (
        f"/**\n * Automated tests for the Orbit {component} component.\n */\n\n"
        + imports
        + f'import {component} from "./{component}";\n'
        + f'import {{ {api_functions[component]} }} from "../api";\n\n'
    )

    functions = [name.strip() for name in api_functions[component].split(",")]
    mocks = "\n".join(f"  {name}: vi.fn()," for name in functions)

    setup = (
        "/** Mock API calls to isolate frontend behavior from the backend. */\n"
        'vi.mock("../api", () => ({\n'
        + mocks
        + "\n}));\n\n"
        "/** Reset rendered components and API mocks between tests. */\n"
        "afterEach(() => {\n"
        "  cleanup();\n"
        "  vi.resetAllMocks();\n"
        "});\n\n"
    )

    fixture = ""
    if component == "UserProfile":
        fixture_start = content.index("const regularProfile =")
        fixture_end = content.index("};", fixture_start) + 2
        fixture_comment = content.rfind("/**", 0, fixture_start)
        fixture = content[fixture_comment:fixture_end] + "\n\n"

    target = directory / filename
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {target}")

    target.write_text(header + setup + fixture + section)
    print(f"Created {target}")

source.unlink()
print(f"Removed {source}")
