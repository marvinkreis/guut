```
{% if is_debugger %}
{{ result | format_debugger_result }}
{% else %}
{{ result | format_test_result }}
{% endif %}
```
{% if result.timeout %}
The {{ name }} was canceled due to a timeout{% if result.exitcode != 0 %} and exited with exit code {{ result.exitcode }}{% endif %}.

{% elif result.exitcode != 0 %}
The {{ name }} exited with exit code {{ result.exitcode }}.
{% endif %}
