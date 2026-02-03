# ruff: noqa
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
PRODUCTION_DOTENVS_DIR = BASE_DIR / ".envs" / ".production"
PRODUCTION_DOTENV_FILES = [
    PRODUCTION_DOTENVS_DIR / ".django",
    PRODUCTION_DOTENVS_DIR / ".postgres",
]
DOTENV_FILE = BASE_DIR / ".env"


def _resolve_under_base(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    base_resolved = base.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Path {resolved} is not under {base_resolved}") from None
    return resolved


def merge() -> None:
    out = _resolve_under_base(DOTENV_FILE, BASE_DIR)
    merged_content = "" #NOSONAR (S2083) "This is a merge of production dotenv files into the main dotenv file"
    for merge_file in PRODUCTION_DOTENV_FILES: #NOSONAR (S2083) "This is a merge of production dotenv files into the main dotenv file"
        src = _resolve_under_base(merge_file, BASE_DIR) #NOSONAR (S2083) "This is a merge of production dotenv files into the main dotenv file"
        merged_content += src.read_text() #NOSONAR (S2083) "This is a merge of production dotenv files into the main dotenv file"
        merged_content += os.linesep #NOSONAR (S2083) "This is a merge of production dotenv files into the main dotenv file"
    out.write_text(merged_content) #NOSONAR (S2083) "This is a merge of production dotenv files into the main dotenv file"


if __name__ == "__main__":
    merge()
