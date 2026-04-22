import subprocess
import tempfile
import ipaddress
from langchain.agents import Tool

def run_searchsploit(query: str) -> str:
    query = query.strip()
    if not query:
        return "Error: no search term provided to SearchSploit."

    def normal_search(q: str) -> str:
        cmd = ["searchsploit"] + q.split()
        sp2 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if sp2.stderr and not sp2.stdout.strip():
            return f"Error: {sp2.stderr.strip()}"
        return sp2.stdout.strip()

    try:
        ipaddress.ip_address(query)
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            xml_path = tmp.name
        nm = subprocess.run(
            ["nmap", "-sV", "-oX", xml_path, query],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if nm.stderr:
            return f"Nmap error: {nm.stderr.strip()}"
        sp = subprocess.run(
            ["searchsploit", "--nmap", "-v", xml_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if sp.stderr:
            err = sp.stderr.strip()
            if "Could not find file" in err:
                return normal_search(query)
            return f"SearchSploit error: {err}"
        return sp.stdout.strip()
    except ValueError:
        return normal_search(query)
    except Exception as e:
        return f"Exception occurred in run_searchsploit: {e}"

searchsploit_tool = Tool(
    name="SearchSploit",
    func=run_searchsploit,
    description=(
        "Use this tool to search Exploit-DB for known vulnerabilities. "
        "Input should be the search term (e.g., software name, CVE, or IP)."
    )
)

