from flask import Flask, request, jsonify, render_template, send_file
from agents import AgentManager
import json
import tempfile
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
agent_manager = AgentManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agents', methods=['POST'])
def create_agent():
    try:
        agent_data = request.json
        if not agent_data:
            return jsonify({"error": "No data provided"}), 400
            
        logger.info(f"Creating new agent with data: {json.dumps(agent_data, indent=2)}")
        agent = agent_manager.create_agent(agent_data)
        logger.info(f"Agent created successfully: {json.dumps(agent.to_dict(), indent=2)}")
        return jsonify(agent.to_dict()), 201
    except ValueError as e:
        logger.error(f"Validation error while creating agent: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error while creating agent: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/agents', methods=['GET'])
def get_agents():
    try:
        agents = [agent.to_dict() for agent in agent_manager.get_all_agents()]
        logger.info(f"Retrieved all agents: {json.dumps(agents, indent=2)}")
        return jsonify(agents)
    except Exception as e:
        logger.error(f"Error fetching agents: {str(e)}")
        return jsonify({"error": f"Error fetching agents: {str(e)}"}), 500

@app.route('/agents/get', methods=['POST'])
def get_agent():
    try:
        data = request.json
        if not data or 'agent_id' not in data:
            return jsonify({"error": "agent_id is required"}), 400
            
        agent_id = data['agent_id']
        logger.info(f"Fetching agent with ID: {agent_id}")
        agent = agent_manager.get_agent(agent_id)
        
        if agent:
            logger.info(f"Agent found: {json.dumps(agent.to_dict(), indent=2)}")
            return jsonify(agent.to_dict())
        logger.warning(f"Agent not found with ID: {agent_id}")
        return jsonify({"error": "Agent not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching agent: {str(e)}")
        return jsonify({"error": f"Error fetching agent: {str(e)}"}), 500

@app.route('/agents/chat', methods=['POST'])
def chat_with_agent():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        agent_id = data.get('agent_id')
        message = data.get('message')
        
        if not agent_id:
            return jsonify({"error": "agent_id is required"}), 400
        if not message:
            return jsonify({"error": "message is required"}), 400
        
        logger.info(f"Processing chat message for agent {agent_id}: {message}")
        response = agent_manager.process_message(agent_id, message)
        logger.info(f"Chat response generated for agent {agent_id}: {response}")
        return jsonify({"response": response})
    except ValueError as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"error": f"Error processing message: {str(e)}"}), 500

@app.route('/agents/export/<agent_id>', methods=['GET'])
def export_agent(agent_id):
    try:
        logger.info(f"Exporting agent with ID: {agent_id}")
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agent not found for export with ID: {agent_id}")
            return jsonify({"error": "Agent not found"}), 404

        # Create agent export data
        export_data = agent.to_dict()
        logger.info(f"Agent data prepared for export: {json.dumps(export_data, indent=2)}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump(export_data, temp_file, indent=2)
            temp_path = temp_file.name

        # Send the file and then delete it
        response = send_file(
            temp_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'agent_{agent.name.lower().replace(" ", "_")}.json'
        )
        
        # Delete the temp file after sending
        @response.call_on_close
        def cleanup():
            os.remove(temp_path)
            logger.info(f"Temporary export file deleted: {temp_path}")
            
        logger.info(f"Agent {agent_id} exported successfully")
        return response
    except Exception as e:
        logger.error(f"Error exporting agent: {str(e)}")
        return jsonify({"error": f"Error exporting agent: {str(e)}"}), 500

@app.route('/agents/import', methods=['POST'])
def import_agent():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        if not file.filename.endswith('.json'):
            return jsonify({"error": "Only JSON files are allowed"}), 400

        logger.info(f"Importing agent from file: {file.filename}")
        # Read and parse the JSON file
        try:
            agent_data = json.load(file)
            logger.info(f"Agent data parsed from import file: {json.dumps(agent_data, indent=2)}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON file during import: {file.filename}")
            return jsonify({"error": "Invalid JSON file"}), 400

        # Create new agent from imported data
        agent = agent_manager.create_agent(agent_data)
        logger.info(f"Agent imported successfully: {json.dumps(agent.to_dict(), indent=2)}")
        return jsonify(agent.to_dict()), 201
    except ValueError as e:
        logger.error(f"Validation error during import: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error importing agent: {str(e)}")
        return jsonify({"error": f"Error importing agent: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True) 