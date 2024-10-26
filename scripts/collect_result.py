import json
import sys
from pathlib import Path

results_dir = Path(sys.argv[1])

collected_data = {
    "mutants": [],
    "alive_mutants": [],
    "killed_mutants": [],
    "tests": [],
}

for loop_dir in (results_dir / "loops").iterdir():
    result_file = loop_dir / "result.json"
    with result_file.open("r") as f:
        result = json.load(f)

    problem_desc = result["problem"]
    mutant = {
        "target_path": problem_desc["target_path"],
        "mutant_op": problem_desc["mutant_op"],
        "occurrence": problem_desc["occurrence"],
    }

    collected_data["mutants"].append(mutant)
    if result["mutant_killed"]:
        collected_data["killed_mutants"].append(mutant)

        killing_test = result["tests"][-1]
        collected_data["tests"].append((result["long_id"], killing_test))
    else:
        collected_data["alive_mutants"].append(mutant)


with (results_dir / "result.json").open("w") as f:
    json.dump(collected_data, f)
