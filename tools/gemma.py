from pathlib import Path
import subprocess

from tools.inference import generate_response
from tools.nmap import nmap_tool
from tools.searchsploit import searchsploit_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "config" / "sys_msg.txt"
SHELL_TIMEOUT_SECONDS = 30
TOOL_PREFIXES = ("Shell:", "Nmap Scanner:", "SearchSploit:")


def load_system_prompt() -> str:
    with SYSTEM_PROMPT_PATH.open("r", encoding="utf-8") as f:
        return f.read().strip()


def build_prompt(user_prompt: str) -> str:
    return f"{load_system_prompt()}\n\nUser: {user_prompt}\nSydney:"


def run_shell_command(command: str) -> str:
    if not command:
        return "Error: no shell command provided."

    try:
        proc = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
        )
        out = proc.stdout.strip() or proc.stderr.strip()
        return f"$ {command}\n{out}"
    except subprocess.TimeoutExpired:
        return (
            f"Error running shell command '{command}': "
            f"timed out after {SHELL_TIMEOUT_SECONDS} seconds."
        )
    except Exception as e:
        return f"Error running shell command '{command}': {e}"


def execute_tool_calls(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("Shell:"):
            return run_shell_command(line[len("Shell:"):].strip())

        if line.startswith("Nmap Scanner:"):
            target = line[len("Nmap Scanner:"):].strip()
            try:
                out = nmap_tool.func(target)
                return f"Nmap results for {target}:\n{out}"
            except Exception as e:
                return f"Error running Nmap on '{target}': {e}"

        if line.startswith("SearchSploit:"):
            query = line[len("SearchSploit:"):].strip()
            try:
                out = searchsploit_tool.func(query)
                return f"Searchsploit results for '{query}':\n{out}"
            except Exception as e:
                return f"Error running SearchSploit for '{query}': {e}"

        return line

    return ""


def handle_prompt(prompt: str) -> str:
    if prompt.strip().startswith(TOOL_PREFIXES):
        return execute_tool_calls(prompt)

    raw_response = generate_response(build_prompt(prompt))
    return execute_tool_calls(raw_response)


if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        result = handle_prompt(user_input)
        print(f"Sydney:\n{result}\n")
