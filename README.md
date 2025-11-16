# 🤖 SupportPilot

**AI-Powered IT Support System with Multi-Agent Architecture**

SupportPilot is an intelligent IT support assistant built using Google's Agent Development Kit (ADK). It demonstrates a production-ready multi-agent system that automatically resolves Level 1 support issues and escalates complex problems to Level 2 human support.

---

## 🎯 Project Overview

**Kaggle Capstone Project - AI Agents Course**

This project showcases:
- ✅ **Multi-agent system** (4 specialized agents)
- ✅ **Custom tools** (3 tools with detailed specifications)
- ✅ **Session & state management** (ADK-compatible)
- ✅ **Observability** (Tracing, logging, metrics)
- ✅ **Negative signal detection** (intelligent escalation)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│          ORCHESTRATOR AGENT                 │
│  • Classifies user intent                   │
│  • Detects dissatisfaction                  │
│  • Delegates to specialized agents          │
└──────────┬────────────────┬─────────────────┘
           │                │          
      ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐
      │KNOWLEDGE │    │CREATION  │    │  QUERY   │
      │  AGENT   │    │  AGENT   │    │  AGENT   │
      │  (L1)    │    │  (L2)    │    │ (Status) │
      └────┬─────┘    └────┬─────┘    └────┬─────┘
           │               │                │
      ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐
      │search_kb │    │create_   │    │get_ticket│
      │   tool   │    │ticket    │    │_status   │
      └──────────┘    └──────────┘    └──────────┘
```

### Agents

1. **Orchestrator Agent** (Brain)
   - Entry point for all user requests
   - Classifies intent (FAQ, Ticket, Status)
   - Detects negative signals ("didn't work", "still broken")
   - Routes to appropriate specialist

2. **Knowledge Agent** (L1 Support)
   - Searches knowledge base for solutions
   - Resolves common IT issues
   - Returns "KB_NOT_FOUND" if no solution exists

3. **Creation Agent** (L2 Escalation)
   - Creates support tickets
   - Assesses priority (Low/Normal/High)
   - Provides ticket confirmation

4. **Query Agent** (Status Checker)
   - Retrieves user's tickets
   - Formats status information
   - Explains ticket states

### Tools

1. **search_knowledge_base(query: str)**
   - Searches 20-article IT support knowledge base
   - Returns step-by-step solutions
   - Uses keyword matching

2. **create_support_ticket(user_id, description, priority, trace_id)**
   - Creates tickets in SQLite database
   - Generates unique ticket IDs
   - Tracks escalation metadata

3. **get_ticket_status(user_id: str)**
   - Queries all user tickets
   - Returns status (Open/In Progress/Closed)
   - Orders by creation date

---

## 📊 Key Features

### Intelligent Escalation
- **Auto-escalation**: KB not found → automatic ticket creation
- **Negative signal detection**: User dissatisfaction triggers L2 escalation
- **Context preservation**: Previous attempts tracked in ticket description

### Observability
- **Tracing**: UUID-based request tracking
- **Decision logging**: All routing decisions recorded
- **Metrics**: L1 vs L2 resolution rates, response times

### Session Management
- **ADK-compatible**: Works with InMemorySessionService
- **Custom metadata**: Business logic state (kb_attempted, escalated)
- **Conversation history**: Full context preservation

---

## 🚀 Installation

### Prerequisites
- Python 3.9+
- Google AI API key ([Get one here](https://aistudio.google.com/app/apikey))

### Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd SupportPilot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 5. Initialize database (automatic on first run)
# Knowledge base is in data/knowledge_base.json
```

---

## 💻 Usage

### Interactive Mode

```bash
python src/main.py
```

Chat with SupportPilot:
```
👤 You: My VPN is not connecting
🤖 SupportPilot: I found a solution for this issue:

VPN Connection Issues

Steps:
1. Check your internet connection is working
2. Restart your router/modem
3. Close and reopen the VPN client application
...
```

### Demo Mode (for Video)

```bash
python src/main.py --demo
```

Runs 5 predefined scenarios showcasing all features:
1. ✅ L1 Resolution (KB success)
2. ✅ Auto-escalation (KB not found)
3. ✅ Negative signal detection
4. ✅ Explicit ticket request
5. ✅ Status query

### Commands

- `/help` - Show available commands
- `/status` - View metrics (L1/L2 rates)
- `/reset` - Clear conversation history
- `/quit` - Exit

---

## 📁 Project Structure

```
SupportPilot/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # API key template
│
├── data/
│   ├── knowledge_base.json      # 20 IT support articles
│   └── service_desk.db          # SQLite tickets (auto-generated)
│
├── prompts/
│   ├── knowledge_agent.prompt   # L1 system instructions
│   ├── creation_agent.prompt    # L2 system instructions
│   └── query_agent.prompt       # Status system instructions
│
└── src/
    ├── main.py                  # CLI entry point
    │
    ├── agents/
    │   ├── orchestrator.py      # Main coordinator
    │   ├── knowledge_agent.py   # L1 specialist
    │   ├── creation_agent.py    # L2 specialist
    │   └── query_agent.py       # Status specialist
    │
    ├── tools/
    │   └── support_tools.py     # 3 custom tools + ADK declarations
    │
    ├── core/
    │   ├── database.py          # SQLite + JSON KB
    │   └── observability.py     # Tracing + Metrics
    │
    └── models/
        └── session.py           # Session metadata (ADK-compatible)
```

---

## 🎬 Demo Scenarios

### Scenario 1: Happy Path
**Input**: "My VPN is not connecting"  
**Flow**: Orchestrator → Knowledge Agent → KB found → Solution presented  
**Result**: ✅ L1 Resolution

### Scenario 2: Auto-Escalation
**Input**: "Help with quantum computing integration"  
**Flow**: Orchestrator → Knowledge Agent → KB_NOT_FOUND → Creation Agent  
**Result**: ✅ Ticket created automatically

### Scenario 3: Negative Signal
**Input 1**: "My printer is not working"  
**Response**: KB solution provided  
**Input 2**: "I tried all that and it still doesn't work"  
**Flow**: Negative signal detected → Escalation → Ticket created  
**Result**: ✅ Intelligent escalation

### Scenario 4: Direct Request
**Input**: "I need to create a ticket for battery replacement"  
**Flow**: Orchestrator → Creation Agent (bypasses KB)  
**Result**: ✅ Direct ticket creation

### Scenario 5: Status Query
**Input**: "What are my tickets?"  
**Flow**: Orchestrator → Query Agent → Tickets retrieved  
**Result**: ✅ Status information displayed

---

## 📈 Metrics Example

```
╔═══════════════════════════════════════╗
║     SupportPilot Metrics Report       ║
╚═══════════════════════════════════════╝

Total Requests: 10

Resolution Breakdown:
  • L1 (Knowledge Base): 6 (60%)
  • L2 (Ticket Created): 4 (40%)

Performance:
  • Avg Response Time: 1.2s
  
User Satisfaction:
  • Negative Signals: 2
```

---

## 🧪 Testing

Run the demo mode to verify all components:

```bash
python src/main.py --demo
```

Expected output:
- ✅ All 5 scenarios execute successfully
- ✅ Metrics show L1/L2 split
- ✅ Agent flow traced in logs

---

## 🔧 Configuration

### Environment Variables

```bash
GOOGLE_API_KEY=your-api-key-here
```

### Model Selection

Change in `src/agents/orchestrator.py`:
```python
orchestrator = OrchestratorAgent(model_name="gemini-2.0-flash-exp")
```

Available models:
- `gemini-2.0-flash-exp` (recommended)
- `gemini-1.5-pro`
- `gemini-1.5-flash`

---

## 📚 Knowledge Base

The system includes 20 synthetic IT support articles covering:
- Network issues (VPN, WiFi, shared drives)
- Authentication (passwords, MFA)
- Email problems (sync, Outlook)
- Hardware (printers, USB, monitors, laptops)
- Software (installation, performance)
- Communication tools (Zoom, Teams)

Articles are in `data/knowledge_base.json` and can be easily extended.

---

## 🎓 Learning Outcomes (Kaggle Capstone)

This project demonstrates:

1. **Multi-agent coordination**: Orchestrator delegates to specialists
2. **Tool design**: Clear input/output specifications for LLM understanding
3. **State management**: ADK-compatible session metadata
4. **Observability**: Comprehensive tracing and metrics
5. **Error handling**: Graceful degradation and fallbacks
6. **Real-world applicability**: Solves actual IT support workflow

---

## 🚧 Future Enhancements

- [ ] Vector embeddings for semantic KB search
- [ ] A2A Protocol for true multi-agent communication
- [ ] DatabaseSessionService for persistent sessions
- [ ] Sentiment analysis for better dissatisfaction detection
- [ ] Integration with real ticketing systems (Jira, ServiceNow)
- [ ] Web UI using Gradio or Streamlit

---

## 📝 License

MIT License - Feel free to use this project for learning and adaptation.

---

## 👤 Author

**Your Name**  
Kaggle Capstone Project - AI Agents Course  
November 2025

---

## 🙏 Acknowledgments

- Google Agent Development Kit (ADK) team
- Kaggle AI Agents course instructors
- Anthropic Claude for development assistance