from example import count_names

# The mutant code never increases the name count past 1.
counts = count_names(["Alice", "Alice"])
assert counts["Alice"] == 2, "Alice appears in the list twice"
