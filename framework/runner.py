import subprocess
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def compile_cpp(solution_path, work_dir=None):
    solution_path = Path(solution_path)
    if work_dir is None:
        work_dir = solution_path.parent
    else:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

    ext = ".exe" if sys.platform == "win32" else ""
    exe_name = f"solution{ext}"
    exe_path = work_dir / exe_name

    cmd = ["g++", "-std=c++17", "-O2", "-o", str(exe_path), str(solution_path)]
    logger.info(f"Compiling {solution_path.name}")
    logger.debug(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        logger.error(f"Compilation failed:\n{result.stderr}")
        raise RuntimeError(f"Compilation failed:\n{result.stderr}")

    logger.info(f"Compiled successfully: {exe_path}")
    return exe_path


def run_cpp(exe_path, input_path, timeout=5):
    exe_path = Path(exe_path)
    input_path = Path(input_path)

    with open(input_path, "r", newline="") as f:
        result = subprocess.run(
            [str(exe_path)],
            input=f.read(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"Solution crashed (exit {result.returncode}):\n{result.stderr}"
        )

    return result.stdout


def normalize_output(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    text = "\n".join(lines)
    if text:
        text += "\n"
    return text


def cleanup_exe(exe_path):
    exe_path = Path(exe_path)
    if exe_path.exists():
        try:
            exe_path.unlink()
        except OSError:
            pass
