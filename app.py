from flask import Flask, request, jsonify, render_template, session
from models.fsm import ConversationalAlarmFSM
import uuid
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Store FSM instances per session
fsm_sessions = {}

def get_or_create_fsm():
    """Get or create FSM instance for current session"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    if session_id not in fsm_sessions:
        fsm_sessions[session_id] = ConversationalAlarmFSM()
    
    return fsm_sessions[session_id]

def parse_sql_for_display(sql_query, entities):
    """Parse SQL to extract alarm information for display"""
    if not sql_query or sql_query.startswith('--'):
        return None
    
    # Extract alarm info from entities
    alarm_info = {
        'id': str(uuid.uuid4())[:8],
        'label': entities.get('label', 'Unnamed Alarm'),
        'time': entities.get('time', 'Not specified'),
        'date': entities.get('date', datetime.now().strftime('%Y-%m-%d')),
        'repeat': entities.get('repeat', 'None'),
        'status': 'active' if 'INSERT' in sql_query else 'updated',
        'created_at': datetime.now().strftime('%H:%M:%S')
    }
    
    return alarm_info

@app.route('/')
def home():
    # Initialize new session
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({
                "response": "I didn't receive your message. Could you try again?",
                "state": "error",
                "sql_query": "",
                "alarm_data": None,
                "conversation_stats": {}
            })

        user_input = data["message"]
        fsm = get_or_create_fsm()
        
        # Store previous state for comparison
        prev_state = fsm.state
        prev_entities = fsm.entities.copy()
        
        # Process input through FSM
        response = fsm.process_input(user_input)
        
        # Extract SQL query if generated
        sql_query = ""
        alarm_data = None
        
        # Check if action was executed (SQL generated)
        if "SQL:" in response:
            sql_start = response.find("💾 SQL:") + 8
            sql_end = response.find("\n\n", sql_start)
            if sql_end == -1:
                sql_end = len(response)
            sql_query = response[sql_start:sql_end].strip()
            
            # Clean up response (remove SQL from display)
            response = response[:response.find("💾 SQL:")].strip()
            if response.endswith("\n"):
                response = response[:-1]
            
            # Parse alarm data for frontend display
            alarm_data = parse_sql_for_display(sql_query, fsm.entities)
        
        # Get conversation statistics
        stats = fsm.get_conversation_stats()
        
        return jsonify({
            "response": response,
            "state": fsm.state,
            "current_intent": fsm.current_intent,
            "entities": fsm.entities,
            "missing_fields": fsm.missing_fields,
            "sql_query": sql_query,
            "alarm_data": alarm_data,
            "conversation_stats": stats,
            "user_name": fsm.user_name
        })
        
    except Exception as e:
        return jsonify({
            "response": f"Sorry, I encountered an error: {str(e)}. Let's start fresh!",
            "state": "error",
            "sql_query": "",
            "alarm_data": None,
            "conversation_stats": {}
        }), 500

@app.route('/reset', methods=['POST'])
def reset_conversation():
    """Reset the conversation state"""
    try:
        fsm = get_or_create_fsm()
        fsm.reset()
        
        return jsonify({
            "response": fsm.get_random_response("greetings"),
            "state": "IDLE",
            "message": "Conversation reset successfully!"
        })
    except Exception as e:
        return jsonify({
            "response": "Hi! I'm your alarm assistant. How can I help you today?",
            "state": "IDLE",
            "message": f"Reset with error: {str(e)}"
        })

@app.route('/help', methods=['GET'])
def get_help():
    """Get help information"""
    fsm = get_or_create_fsm()
    help_text = fsm.show_help()
    
    return jsonify({
        "response": help_text,
        "state": "help"
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get conversation statistics"""
    try:
        fsm = get_or_create_fsm()
        stats = fsm.get_conversation_stats()
        conversation_log = fsm.export_conversation_log()
        
        return jsonify({
            "stats": stats,
            "log": conversation_log
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "stats": {},
            "log": {}
        })

@app.route('/demo', methods=['GET'])
def run_demo():
    """Run a demo conversation"""
    fsm = ConversationalAlarmFSM()  # Create fresh instance for demo
    
    demo_inputs = [
        "Hi there, I'm Alex",
        "I need to set an alarm called workout",
        "7:30 AM", 
        "tomorrow",
        "yes",
        "show my alarms",
        "extend workout alarm by 10 minutes",
        "yes"
    ]
    
    demo_conversation = []
    for user_input in demo_inputs:
        response = fsm.process_input(user_input)
        demo_conversation.append({
            "user": user_input,
            "bot": response,
            "state": fsm.state,
            "entities": fsm.entities.copy()
        })
    
    return jsonify({
        "demo_conversation": demo_conversation,
        "final_stats": fsm.get_conversation_stats()
    })

if __name__ == '__main__':
    print("🚀 Enhanced Conversational Alarm Flask App Starting...")
    print("📱 Features:")
    print("   • Multi-state conversation flow")
    print("   • Natural language processing")
    print("   • Entity validation & collection")
    print("   • SQL query generation")
    print("   • Session management")
    print("   • Real-time conversation stats")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)