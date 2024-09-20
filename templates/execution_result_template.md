```
{% if is_debugger %}
{{ result | format_debugger_result }}
{% else %}
{{ result | format_test_result }}
{% endif %}
```
{% if result.timeout %}
The {{ name }} was canceled due to a timeout{% if result.exitcode != 0 %} and exited with exit code {{ result.exitcode }}{% endif %}.
{% if not result.output.strip() %}
Empty experiment output means that no print statement was executed. To fix this, print any results from the correct code before calling the mutant.
{% endif %}

{% elif result.exitcode != 0 %}
The {{ name }} exited with exit code {{ result.exitcode }}.
{% endif %}
