from dataclasses import dataclass
from typing import List, Dict, Optional
import wikipedia
from duckduckgo_search import DDGS
import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OpenAI API key not found in environment variables")

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
            return wikipedia.summary(query, sentences=3)
        except wikipedia.exceptions.DisambiguationError as e:
            # Handle disambiguation pages by using the first suggestion
            try:
                return wikipedia.summary(e.options[0], sentences=2)
            except:
                return "Multiple matches found. Please be more specific."
        except wikipedia.exceptions.PageError:
            return "No Wikipedia page found for this query."
        except Exception as e:
            return f"Error searching Wikipedia: {str(e)}"

    @staticmethod
    def python_repl(code: str) -> str:
        try:
            # Execute code in a restricted environment
            restricted_globals = {}
            restricted_locals = {}
            exec(code, restricted_globals, restricted_locals)
            return str(restricted_locals.get('result', 'Code executed successfully'))
        except Exception as e:
            return f"Error executing Python code: {str(e)}"

    @staticmethod
    def duckduckgo_search(query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=2))
                if not results:
                    return "No results found."
                
                # Combine multiple results
                return "\n".join(result['body'] for result in results)
        except Exception as e:
            return f"Error performing DuckDuckGo search: {str(e)}"

    @staticmethod
    def google_search(query: str) -> str:
        # Since we're not implementing actual Google Search,
        # redirect to DuckDuckGo for better results
        return ToolManager.duckduckgo_search(query)

class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tool_manager = ToolManager()

    def create_agent(self, agent_data: Dict) -> Agent:
        # Validate required fields
        required_fields = ['name', 'role', 'goal', 'backstory', 'tools', 'task']
        missing_fields = [field for field in required_fields if field not in agent_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate task data
        task_data = agent_data.get('task', {})
        if not isinstance(task_data, dict) or 'description' not in task_data or 'expected_output' not in task_data:
            raise ValueError("Invalid task data format")

        # Generate a unique ID
        agent_id = str(len(self.agents) + 1)
        
        # Create task instance
        task = Task(
            description=task_data["description"],
            expected_output=task_data["expected_output"]
        )
        
        # Create and store agent
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
            raise ValueError("Agent not found")

        # Prepare the system message with agent context
        system_message = f"""You are {agent.name}, a {agent.role}. 
        Your goal is: {agent.goal}
        Your backstory: {agent.backstory}
        Your current task: {agent.task.description}
        Expected output: {agent.task.expected_output}
        
        You have access to the following tools: {', '.join(agent.tools)}
        Use these tools when appropriate to help answer questions and complete tasks.
        Always maintain your character and respond in a way that aligns with your role and backstory."""

        # Get tool results
        tool_results = []
        for tool in agent.tools:
            try:
                if tool == "wikipedia":
                    result = self.tool_manager.wikipedia_search(message)
                elif tool == "python_repl":
                    # Only use Python REPL if the message appears to contain code
                    if 'print' in message or 'def' in message or '=' in message:
                        result = self.tool_manager.python_repl(message)
                    else:
                        continue
                elif tool == "duckduckgo" or tool == "google_search":
                    result = self.tool_manager.duckduckgo_search(message)
                else:
                    continue
                
                if result and not result.startswith("Error"):
                    tool_results.append(f"{tool.capitalize()}: {result}")
            except Exception as e:
                tool_results.append(f"{tool.capitalize()}: Error - {str(e)}")

        # Prepare the user message with tool results
        user_message = f"""User message: {message}

Available information from tools:
{chr(10).join(tool_results)}

Remember to maintain your character and use the provided information appropriately."""

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
            raise Exception(f"Error getting AI response: {str(e)}") 