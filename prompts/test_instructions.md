## Test Output

### Instructions

Please continue by writing a test that kills the mutant. The test should pass when executed on the correct code but fail on the mutant.

Please output the test as a simple python snippet. Don't put it into a function. For example:

```python
from example import example

# The mutant code never increases the name count past 1.
counts = example(["Alice", "Alice"])
assert counts["Alice"] == 2, "Alice appears in the list twice"
```

### Test
