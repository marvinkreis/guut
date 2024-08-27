# Test Results

## Test on correct code
```
{{ result.correct | format_test_result }}
```
{% if result.correct.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.correct.exitcode != 0 %}
The test exited with exitcode {{ result.correct.exitcode }}.
{% endif %}

## Test on mutant
```
{{ result.mutant | format_test_result }}
```
{% if result.mutant.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.mutant.exitcode != 0 %}
The test exited with exitcode {{ result.mutant.exitcode }}.
{% endif %}

Your test did not correctly identify the mutant. Please try again.
