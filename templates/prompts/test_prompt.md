{% if max_iterations %}
<DEBUGGING_DONE>

{% endif %}
# Test Instructions

## Instructions

{% if max_iterations %}
You've reached the maximum number of iterations.
{% endif %}

Please continue by writing a test that kills the mutant. Remember, the test should pass when executed on the correct code but fail on the mutant.

Remember: In the test case, you cannot import the mutant like in the previous experiments. Instead, only import the correct version and write a test that passes, but fails if the the correct version is replaced by the mutant version.

So for example, if your experiment looked like this

```python
from example import gcd
from mutant.example import gcd as gcd_mutant

print("Correct code: " + gcd(25, 5))
print("Mutant code: " + gcd_mutant(25, 5))
```

a resulting test could be:

```python
from example import gcd

assert gcd(25, 5) == 5, "some explanation"
```

## Format

Please output the test as a simple python snippet. Don't put it into a function and don't use any framework. Remember that you cannot import the mutant.

# Test Case
