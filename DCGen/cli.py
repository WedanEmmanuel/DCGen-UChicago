
import runpy
import pathlib
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime



def run_examples():
    base_dir = pathlib.Path(__file__).parent.parent
    examples_dir = base_dir / "examples"
    logs_dir = examples_dir / "logs"

    if not examples_dir.exists():
        raise RuntimeError(f"Examples directory ({examples_dir}) not found ")

    logs_dir.mkdir(parents=True, exist_ok=True)

    for example in sorted(examples_dir.glob("*.py")):
        '''timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"{example.stem}_{timestamp}.log"'''

        log_file = logs_dir / f"{example.stem}.log"

        print(f"\n=== Running {example.name} ===")
        print(f"    Log: {log_file}")

        with log_file.open("w") as f, \
             redirect_stdout(f), \
             redirect_stderr(f):

            try:
                runpy.run_path(str(example), run_name="__main__")
            except Exception as e:
                print(f"\nERROR while running {example.name}:")
                print(e)
                
