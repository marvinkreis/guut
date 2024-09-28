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

{% if result.correct.exitcode != 0 %}
Your test needs to pass when executed with the baseline. Adjust the part of your test that caused this error.
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

{% if no_asserts and (result.correct.exitcode == 0) and (result.mutant.exitcode == 0) %}
Your test contains no assertions! Add assertions to your test, so that the test fails when executed with the mutant.
{% endif %}

Your test did not correctly identify the mutant. Remember: Your test needs to pass when executed with the baseline, and fail when executed with the mutant. Please adjust your test case{% if not baseline %} or perform more experiments{% endif %}.
