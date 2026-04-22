import subprocess
from langchain.agents import Tool

def run_nmap(target: str) -> str:
    try:
        command = ["nmap", "-sV", target]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stderr:
            return f"Error: {result.stderr}"
        return result.stdout
    except Exception as e:
        return f"Exception occurred: {str(e)}"

nmap_tool = Tool(
    name="Nmap Scanner",
    func=run_nmap,
    description=(
        "Use this tool to perform an nmap service/version scan on a target IP address. "
        "Do not include any extra text; output should be a concise scan report."
    )
)

