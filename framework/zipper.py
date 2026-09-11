import re
import zipfile
from pathlib import Path


def _case_number(path):
    m = re.search(r"(\d+)\.txt$", path.name)
    return int(m.group(1)) if m else 0


def create_problem_zip(tc_dir, output_path, problem_id=None):
    """Create a HackerRank-format testcase ZIP.

    Layout:
        input/input00.txt, input/input01.txt, ...
        output/output00.txt, output/output01.txt, ...

    Sample testcases come first (00, 01, 02), then normal testcases.
    """
    tc_dir = Path(tc_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sample_input_files = sorted(tc_dir.glob("sample_input*.txt"), key=_case_number)
    sample_output_files = sorted(tc_dir.glob("sample_output*.txt"), key=_case_number)

    input_files = sorted(tc_dir.glob("input*.txt"), key=_case_number)
    output_files = sorted(tc_dir.glob("output*.txt"), key=_case_number)

    if len(sample_input_files) != len(sample_output_files):
        raise RuntimeError(
            f"Sample input/output count mismatch: {len(sample_input_files)} inputs, {len(sample_output_files)} outputs"
        )
    if len(input_files) != len(output_files):
        raise RuntimeError(
            f"Input/output count mismatch: {len(input_files)} inputs, {len(output_files)} outputs"
        )

    all_inputs = sample_input_files + input_files
    all_outputs = sample_output_files + output_files

    width = max(2, len(str(len(all_inputs)))) if all_inputs else 2

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, f in enumerate(all_inputs):
            zf.write(f, f"input/input{idx:0{width}d}.txt")
        for idx, f in enumerate(all_outputs):
            zf.write(f, f"output/output{idx:0{width}d}.txt")


def verify_zip(zip_path):
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"Corrupted file in ZIP: {bad}")
        names = [n for n in zf.namelist() if not n.endswith("/")]
        inputs = sorted(n for n in names if n.startswith("input/"))
        outputs = sorted(n for n in names if n.startswith("output/"))
        for name in names:
            if not (name.startswith("input/") or name.startswith("output/")):
                raise RuntimeError(f"Unexpected file in ZIP: {name}")
        if len(inputs) != len(outputs):
            raise RuntimeError(
                f"ZIP input/output mismatch: {len(inputs)} inputs, {len(outputs)} outputs"
            )
        return len(inputs), len(outputs)
