import json
from pathlib import Path


def save_json(filename, data):
    output_dir = Path("output") # name dir
    output_dir.mkdir(exist_ok=True) # do if not

    filepath = output_dir / filename #make file path 

    with open(filepath, "w", encoding="utf-8") as f:
        # dictionary, list -> json
        json.dump(data, f, indent=2) #thut dau dong 2 cach

    print("Saved:", filepath) #give the path line
