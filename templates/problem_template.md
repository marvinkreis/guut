# Task

{% set cut = problem.class_under_test() %}
{{ cut.name }}:
```{{ cut.language }}
{{ cut.content | rtrim | add_line_numbers }}
```
{% for dep in problem.dependencies() %}

{{ dep.name }}:
```{{ dep.language }}
{{ dep.content | rtrim }}
```
{% endfor %}

Mutant Diff:
```diff
{{ problem.mutant_diff() | rtrim }}
```

# Scientific debugging
