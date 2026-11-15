import inspect
from src.interview import evidence_mapper

funcs = inspect.getmembers(evidence_mapper, inspect.isfunction)
for name, func in funcs:
    print(name)
