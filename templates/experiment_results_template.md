## Experiment Results

### Test on correct code
```
{{ result.test_correct | format_test_result }}
```
{% if result.test_correct.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.test_correct.exitcode != 0 %}
The test exited with exitcode {{ result.test_correct.exitcode }}.
{% endif %}

### Test on mutant
```
{{ result.test_mutant | format_test_result }}
```
{% if result.test_mutant.timeout %}
The test was canceled due to a timeout.
{% endif %}
{% if result.test_mutant.exitcode != 0 %}
The test exited with exitcode {{ result.test_mutant.exitcode }}.
{% endif %}

{% if result.debug_correct %}
### Debugger on correct code
```
{{ result.debug_correct | format_debugger_result }}
```
{% endif %}

{% if result.debug_mutant %}
### Debugger on correct code
```
{{ result.debug_mutant | format_debugger_result }}
```
{% endif %}
