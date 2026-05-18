"""
Prevents concurrent file access by orchestrating everything to do with data besides trading.
"""

'''
Once this project is up and running automatically every day, we only want to have two proccesses running at the same time.
One will be this one, run_pipeline.py, and the other will be trade.py. 
This one will coordinate the data flow by calling on the four other python files in this subfolder. 
This is what claude suggests doing:


Q:
Let's talk about concurrent file access again. Basically program_one.py will create a parquet, and then after it is done creating the file and it saves, I want program_two.py to take information from that parquet, and create a new parquet. Then after that is done, I want program_three.py to read the second parquet, proccess it, and create and save a third parquet. Then program_four.py does the same thing, creating a third parquet. How do I best orchestrate this process?

A:
What you're describing is a **pipeline** — a classic pattern where each stage depends on the previous one finishing. Since your stages are strictly sequential (not concurrent), this is actually simpler than the concurrent access problem. There's no race condition because only one program touches a file at a time.

## The cleanest solution: one orchestrator script

Instead of running four scripts manually in four terminals, you write a single script that runs them one after another:

```python
import subprocess

scripts = [
    "category_a/program_one.py",
    "category_a/program_two.py",
    "category_b/program_three.py",
    "category_b/program_four.py",
]

for script in scripts:
    print(f"Running {script}...")
    result = subprocess.run(["python", script], check=True)

print("Pipeline complete.")
```

`check=True` is the important part — if any script crashes or exits with an error, the pipeline stops immediately rather than blindly running the next step on bad data.

You'd run this once and it handles everything in order.

## Even cleaner: just import and call functions

If you're open to it, the most Pythonic approach is to not use `subprocess` at all. Instead of running separate scripts, you import functions from each module and call them in sequence:

```python
from category_a.program_one import run
from category_a.program_two import run as run_two
from category_b.program_three import run as run_three
from category_b.program_four import run as run_four

run()
run_two()
run_three()
run_four()
```

Each `program_x.py` just defines a `run()` function that does its work. This is faster (no subprocess overhead), easier to debug, and keeps everything in one Python process. The parquet files on disk still serve as the handoff points between stages.

## Which to choose

- If the four scripts are already written and self-contained, use the `subprocess` orchestrator — minimal refactoring.
- If you're still building them out, the import/function approach is cleaner and worth structuring around from the start.

Either way, the key insight is that **sequential = simple**. You only need concurrency guards when things overlap in time. Since each program finishes before the next starts, the parquet files are always in a clean state when the next program reads them.
'''