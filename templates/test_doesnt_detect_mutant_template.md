### Test Results

### Output for Correct Code

```
{{ result.correct | format_test_result }}
```
{% if result.correct.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.correct.exitcode != 0 %}
The test exited with exit code {{ result.correct.exitcode }}.
{% endif %}

### Output for Mutant

```
{{ result.mutant | format_test_result }}
```
{% if result.mutant.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.mutant.exitcode != 0 %}
The test exited with exit code {{ result.mutant.exitcode }}.
{% endif %}

Your test did not correctly identify the mutant. Please try again.
Remember: Your test needs to pass when executed with the correct code, and fail when executed with the mutant.
