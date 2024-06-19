from pathlib import Path

prompt_path = Path(__file__).parent.parent / 'prompt'
prompt = prompt_path.read_text()
