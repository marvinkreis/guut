### Test Results

### Running Test on Baseline

```
{{ result.correct | format_test_result }}
```
{% if result.correct.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.correct.exitcode != 0 %}
The test exited with exit code {{ result.correct.exitcode }}.
{% endif %}

### Running Test on Mutant

```
{{ result.mutant | format_test_result }}
```
{% if result.mutant.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.mutant.exitcode != 0 %}
The test exited with exit code {{ result.mutant.exitcode }}.
{% endif %}

Your test did not correctly identify the mutant. Remember: Your test needs to pass when executed with the baseline, and fail when executed with the mutant. When running the test on the mutant, the test needs to result in

- a failed assertion or
- an uncaught exception/error or
- a timeout.

If your test doesn't contain assertions, add assertions. If the mutant raises an exception/error and your test is catching it, remove the try-except block. Adjust your test case{% if not baseline %} or perform more experiments{% endif %}.
