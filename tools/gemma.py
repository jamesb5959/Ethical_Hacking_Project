from typing import Any, List, Optional, Dict, Type
from langchain.chat_models.base import BaseChatModel
from langchain.schema import AIMessage, ChatGeneration, ChatResult, HumanMessage, SystemMessage
from pydantic import Field
import subprocess
from langchain.agents import Tool
from langchain_community.tools.shell.tool import ShellTool
from tools.nmap import nmap_tool
from tools.inference import generate_response
from langgraph.prebuilt import create_react_agent
import os
from tools.searchsploit import searchsploit_tool

class GemmaLLM(BaseChatModel):
    tools: Optional[List[Any]] = Field(default=None)

    def _generate(self, messages: List[Any], stop: Optional[List[str]] = None) -> ChatResult:
        # Load system prompt from external file (moved out of inline string)
        cfg = os.path.join(os.path.dirname(__file__), "config", "sys_msg.txt")
        with open(cfg, "r") as f:
            sys_msg = f.read()

        # Prepend system message
        sys_message = SystemMessage(content=sys_msg)
        inputs = [sys_message] + messages

        # Generate response
        return super()._generate(inputs, stop=stop)


def execute_tool_calls(text: str) -> str:
    outputs = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Shell:"):
            cmd = line[len("Shell:"):].strip()
            try:
                proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out = proc.stdout.strip() or proc.stderr.strip()
                outputs.append(f"$ {cmd}\n{out}")
            except Exception as e:
                outputs.append(f"Error running shell command '{cmd}': {e}")
            break
        elif line.startswith("Nmap Scanner:"):
            ip = line[len("Nmap Scanner:"):].strip()
            try:
                out = nmap_tool.func(ip)
                outputs.append(f"Nmap results for {ip}:\n{out}")
            except Exception as e:
                outputs.append(f"Error running Nmap on '{ip}': {e}")
            break
        elif line.startswith("SearchSploit:"):
            query = line[len("SearchSploit:"):].strip()
            try:
                out = searchsploit_tool.func(query)
                outputs.append(f"Searchsploit results for '{query}':\n{out}")
            except Exception as e:
                outputs.append(f"Error running SearchSploit for '{query}': {e}")
            break
        else:
            outputs.append(line)
            break
    return "\n".join(outputs)

def handle_prompt(prompt: str) -> str:
    gemma_llm = GemmaLLM()
    tools = [ShellTool(), nmap_tool, searchsploit_tool]
    agent = create_react_agent(gemma_llm, tools=tools)
    stream = agent.stream({"messages": [("user", prompt)]}, stream_mode="values")
    raw_response = None
    for s in stream:
        msg = s["messages"][-1]
        raw_response = msg[1] if isinstance(msg, tuple) else msg.content

    # Execute any tool calls and return combined output
    return execute_tool_calls(raw_response or "")

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        result = handle_prompt(user_input)
        print(f"Gemma:\n{result}\n")

