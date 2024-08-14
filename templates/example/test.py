from example import example

# The mutant code never increases the name count past 1.
counts = example(["Alice", "Alice"])
assert counts["Alice"] == 2, "Alice appears in the list twice"
