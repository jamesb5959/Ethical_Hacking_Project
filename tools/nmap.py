import subprocess
from dataclasses import dataclass
from typing import Callable

NMAP_TIMEOUT_SECONDS = 120


@dataclass
class Tool:
    name: str
    func: Callable[[str], str]
    description: str


def run_nmap(target: str) -> str:
    target = target.strip()
    if not target:
        return "Error: no target provided to Nmap Scanner."

    try:
        result = subprocess.run(
            ["nmap", "-sV", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=NMAP_TIMEOUT_SECONDS,
        )
        if result.stderr:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"Error: nmap scan timed out after {NMAP_TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Exception occurred: {e}"


nmap_tool = Tool(
    name="Nmap Scanner",
    func=run_nmap,
    description=(
        "Use this tool to perform an nmap service/version scan on a target IP address. "
        "Do not include any extra text; output should be a concise scan report."
    ),
)
