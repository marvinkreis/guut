# Task

{% set cut = problem.class_under_test() %}
```{{ cut.language }} {{ cut.name }}
{{ problem | format_cut }}
```
{% for dep in problem.dependencies() %}

{{ dep.name }}:
```{{ dep.language }} {{ dep.name }}
{{ dep.content | rtrim }}
```
{% endfor %}

```diff mutant.diff
{{ problem.mutant_diff() | rtrim }}
```

{% if is_baseline %}
# Test
{% else %}
# Debugging
{% endif %}
