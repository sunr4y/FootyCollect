from pathlib import Path

import pytest

import merge_production_dotenvs_in_dotenv as merge_module


@pytest.mark.parametrize(
    ("input_contents", "expected_output"),
    [
        ([], ""),
        ([""], "\n"),
        (["JANE=doe"], "JANE=doe\n"),
        (["SEP=true", "AR=ator"], "SEP=true\nAR=ator\n"),
        (["A=0", "B=1", "C=2"], "A=0\nB=1\nC=2\n"),
        (["X=x\n", "Y=y", "Z=z\n"], "X=x\n\nY=y\nZ=z\n\n"),
    ],
)
def test_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    input_contents: list[str],
    expected_output: str,
):
    output_file = tmp_path / ".env"
    files_to_merge = []
    for num, input_content in enumerate(input_contents, start=1):
        merge_file = tmp_path / f".service{num}"
        merge_file.write_text(input_content)
        files_to_merge.append(merge_file)

    monkeypatch.setattr(merge_module, "DOTENV_FILE", output_file)
    monkeypatch.setattr(merge_module, "PRODUCTION_DOTENV_FILES", files_to_merge)
    monkeypatch.setattr(merge_module, "BASE_DIR", tmp_path)

    merge_module.merge()

    assert output_file.read_text() == expected_output
