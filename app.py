from flask import Flask, request, jsonify, render_template
from agents import AgentManager
import json

app = Flask(__name__)
agent_manager = AgentManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agents', methods=['POST'])
def create_agent():
    try:
        agent_data = request.json
        agent = agent_manager.create_agent(agent_data)
        return jsonify(agent.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/agents', methods=['GET'])
def get_agents():
    agents = [agent.to_dict() for agent in agent_manager.get_all_agents()]
    return jsonify(agents)

@app.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    agent = agent_manager.get_agent(agent_id)
    if agent:
        return jsonify(agent.to_dict())
    return jsonify({"error": "Agent not found"}), 404

@app.route('/agents/<agent_id>/chat', methods=['POST'])
def chat_with_agent(agent_id):
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        response = agent_manager.process_message(agent_id, message)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True) 