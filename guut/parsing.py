def extract_code(response: str, language: str) -> str:
    taking_lines = False
    code_lines = []

    for line in response.splitlines():
        if line.strip() == f'```{language}':
            taking_lines = True
            continue

        if taking_lines and line.strip() == '```':
            break

        if taking_lines:
            code_lines.append(line)

    return '\n'.join(code_lines)
