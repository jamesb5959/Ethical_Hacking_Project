import ipaddress
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Callable

NMAP_TIMEOUT_SECONDS = 120
SEARCHSPLOIT_TIMEOUT_SECONDS = 60


@dataclass
class Tool:
    name: str
    func: Callable[[str], str]
    description: str


def run_searchsploit(query: str) -> str:
    query = query.strip()
    if not query:
        return "Error: no search term provided to SearchSploit."

    def normal_search(search_term: str) -> str:
        result = subprocess.run(
            ["searchsploit", *search_term.split()],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SEARCHSPLOIT_TIMEOUT_SECONDS,
        )
        if result.stderr and not result.stdout.strip():
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()

    xml_path = None
    try:
        ipaddress.ip_address(query)
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            xml_path = tmp.name

        nmap_result = subprocess.run(
            ["nmap", "-sV", "-oX", xml_path, query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=NMAP_TIMEOUT_SECONDS,
        )
        if nmap_result.stderr:
            return f"Nmap error: {nmap_result.stderr.strip()}"

        search_result = subprocess.run(
            ["searchsploit", "--nmap", "-v", xml_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SEARCHSPLOIT_TIMEOUT_SECONDS,
        )
        if search_result.stderr:
            err = search_result.stderr.strip()
            if "Could not find file" in err:
                return normal_search(query)
            return f"SearchSploit error: {err}"
        return search_result.stdout.strip()
    except subprocess.TimeoutExpired as e:
        return f"Error: command timed out after {e.timeout} seconds."
    except ValueError:
        return normal_search(query)
    except Exception as e:
        return f"Exception occurred in run_searchsploit: {e}"
    finally:
        if xml_path:
            try:
                os.unlink(xml_path)
            except OSError:
                pass


searchsploit_tool = Tool(
    name="SearchSploit",
    func=run_searchsploit,
    description=(
        "Use this tool to search Exploit-DB for known vulnerabilities. "
        "Input should be the search term (e.g., software name, CVE, or IP)."
    ),
)
