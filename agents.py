from dataclasses import dataclass
from typing import List, Dict, Optional
import wikipedia
from duckduckgo_search import DDGS
import json
import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

@dataclass
class Task:
    description: str
    expected_output: str

@dataclass
class Agent:
    id: str
    name: str
    role: str
    goal: str
    backstory: str
    task: Task
    tools: List[str]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "task": {
                "description": self.task.description,
                "expected_output": self.task.expected_output
            },
            "tools": self.tools
        }

class ToolManager:
    @staticmethod
    def wikipedia_search(query: str) -> str:
        try:
            return wikipedia.summary(query, sentences=2)
        except:
            return "No Wikipedia results found."

    @staticmethod
    def python_repl(code: str) -> str:
        try:
            # In a real implementation, this would use LangChain's PythonREPLTool
            # For now, we'll just return a mock response
            return f"Executed Python code: {code}"
        except Exception as e:
            return f"Error executing Python code: {str(e)}"

    @staticmethod
    def duckduckgo_search(query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=1))
                return results[0]['body'] if results else "No results found."
        except:
            return "Error performing DuckDuckGo search."

    @staticmethod
    def google_search(query: str) -> str:
        # Mock implementation since we don't have API key
        return f"Google search results for: {query}"

class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tool_manager = ToolManager()

    def create_agent(self, agent_data: Dict) -> Agent:
        agent_id = str(len(self.agents) + 1)
        task = Task(
            description=agent_data["task"]["description"],
            expected_output=agent_data["task"]["expected_output"]
        )
        
        agent = Agent(
            id=agent_id,
            name=agent_data["name"],
            role=agent_data["role"],
            goal=agent_data["goal"],
            backstory=agent_data["backstory"],
            task=task,
            tools=agent_data["tools"]
        )
        
        self.agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

    def get_all_agents(self) -> List[Agent]:
        return list(self.agents.values())

    def process_message(self, agent_id: str, message: str) -> str:
        agent = self.get_agent(agent_id)
        if not agent:
            return "Agent not found."

        # Prepare the system message with agent context
        system_message = f"""You are {agent.name}, a {agent.role}. 
        Your goal is: {agent.goal}
        Your backstory: {agent.backstory}
        Your current task: {agent.task.description}
        Expected output: {agent.task.expected_output}
        
        You have access to the following tools: {', '.join(agent.tools)}
        Use these tools when appropriate to help answer questions and complete tasks."""

        # Get tool results
        tool_results = []
        for tool in agent.tools:
            if tool == "wikipedia":
                tool_results.append(f"Wikipedia: {self.tool_manager.wikipedia_search(message)}")
            elif tool == "python_repl":
                tool_results.append(f"Python REPL: {self.tool_manager.python_repl('print(1+1)')}")
            elif tool == "duckduckgo":
                tool_results.append(f"DuckDuckGo: {self.tool_manager.duckduckgo_search(message)}")
            elif tool == "google_search":
                tool_results.append(f"Google: {self.tool_manager.google_search(message)}")

        # Prepare the user message with tool results
        user_message = f"""User message: {message}

Tool results:
{chr(10).join(tool_results)}"""

        try:
            # Get GPT response
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error getting GPT response: {str(e)}" 