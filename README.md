# ✈️ SupportPilot - AI-Powered IT Support Assistant

**An intelligent multi-agent system built with Google's Agent Development Kit (ADK) to automate IT helpdesk operations with role-based access control.**

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Solution Overview](#-solution-overview)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Setup Instructions](#-setup-instructions)
- [Usage Guide](#-usage-guide)
- [Project Structure](#-project-structure)
- [ADK Concepts Demonstrated](#-adk-concepts-demonstrated)
- [Future Enhancements](#-future-enhancements)
- [Contributing](#-contributing)

---

## 🎯 Problem Statement

Many organizations face **critical resource shortages** in their IT service desks, leading to:
- ⏱️ Long response times for Level 1 support requests
- 📈 Overwhelming ticket volumes for human agents
- 💰 High operational costs for routine troubleshooting
- 😤 User frustration with repetitive issues

**The Challenge:** Build an AI system that can handle Level 1 IT support autonomously while maintaining security, traceability, and seamless escalation to human agents when needed.

---

## 💡 Solution Overview

**SupportPilot** is an enterprise-grade AI assistant that:

1. **Receives** Level 1 IT support requests via a conversational interface
2. **Searches** a knowledge base for documented solutions
3. **Resolves** issues instantly when solutions are found
4. **Escalates** by creating tickets for Level 2 (human) review when needed
5. **Manages** the full ticket lifecycle with role-based permissions

### Core Capabilities

- 🤖 **Autonomous Troubleshooting**: Searches KB and provides step-by-step solutions
- 🎫 **Ticket Management**: Create, view, and update support tickets
- 🔐 **Role-Based Access Control (RBAC)**: Different permissions for end users vs. service desk agents
- 💾 **Persistent Memory**: Maintains conversation context across sessions
- 📊 **Full Observability**: Structured logging for debugging and monitoring

---

## 🏗️ Architecture

### Multi-Agent System Design

SupportPilot uses a **hierarchical multi-agent architecture** with specialized agents:

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
│                    (End User / Service Desk Agent)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                         │
│              (Main Coordinator - LlmAgent)                   │
│  • Intent Recognition                                        │
│  • Request Routing                                           │
│  • Session Management                                        │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌────────────────┐
│  Knowledge  │   │   Ticket    │   │  Session       │
│   Agent     │   │   Agent     │   │  Tools         │
│  (LlmAgent) │   │  (LlmAgent) │   │  (Direct)      │
└──────┬──────┘   └──────┬──────┘   └────────────────┘
       │                 │
       ▼                 ▼
┌─────────────┐   ┌─────────────────────────────────┐
│ KB Search   │   │  Ticket Tools (4 tools)         │
│ Tool        │   │  • create_ticket                │
│             │   │  • get_ticket_by_id             │
│             │   │  • list_all_tickets             │
│             │   │  • update_ticket_status         │
└─────────────┘   └─────────────────────────────────┘
```

### Agent Descriptions

#### 1. **Orchestrator Agent** (Coordinator)
- **Model**: Gemini 2.5 Flash Lite
- **Role**: Main entry point, routes requests to specialized agents
- **Tools**: Knowledge Agent, Ticket Agent, get_my_info

#### 2. **Knowledge Agent** (Technical Support)
- **Model**: Gemini 2.5 Flash Lite
- **Role**: Searches knowledge base for solutions
- **Tools**: search_knowledge_base
- **Output**: Step-by-step troubleshooting instructions

#### 3. **Ticket Agent** (Operations)
- **Model**: Gemini 2.5 Flash Lite
- **Role**: Manages ticket CRUD operations
- **Tools**: 4 ticket management tools
- **RBAC**: Enforces permissions based on user role

### Data Flow Example

```
User: "My VPN is not connecting"
    ↓
Orchestrator: Routes to Knowledge Agent
    ↓
Knowledge Agent: Calls search_knowledge_base("VPN not connecting")
    ↓
Tool: Returns {"status": "success", "message": "SOLUTION: 1. Check internet..."}
    ↓
Knowledge Agent: Formats solution for user
    ↓
Orchestrator: Relays response to user
    ↓
User: Receives step-by-step instructions
```

### Role-Based Access Control (RBAC)

| Role | Create Tickets | View Own Tickets | View All Tickets | Update Tickets |
|------|---------------|------------------|------------------|----------------|
| **end_user** | ✅ | ✅ | ❌ | ❌ |
| **service_desk_agent** | ✅ | ✅ | ✅ | ✅ |

---

## ✨ Key Features

### 1. **Multi-Agent Orchestration**
- Coordinator/Dispatcher multi-agent pattern with clear separation of concerns
- Agents communicate via structured dictionaries (ADK best practice)

### 2. **Knowledge Base Search**
- JSON-based KB with 5 common IT issues (VPN, Printer, Email, Software, Security)
- Keyword matching algorithm
- Returns formatted solutions with step-by-step instructions

### 3. **Ticket Management System**
- **SQLite database** for persistent storage
- **CRUD operations**: Create, Read (by ID and list), Update
- **Priority levels**: Low, Normal, High
- **Status tracking**: Open → In Progress → Closed

### 4. **Session & Memory**
- **DatabaseSessionService** for long-term persistence
- Conversation history maintained across sessions
- User identity and role stored in session state

### 5. **Enhanced Observability**
- **Structured logging** with timestamps and severity levels
- **Tool call tracing**: Every function call and return logged
- **Logs stored** in `logs/support_pilot.log`

### 6. **Security Features**
- User identity from session (not user input)
- Role-based permissions enforced at tool level
- No privilege escalation possible via conversation

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Google ADK | Multi-agent orchestration |
| **LLM** | Gemini 2.5 Flash Lite | Fast, cost-efficient reasoning |
| **Database** | SQLite | Tickets and sessions storage |
| **Knowledge Base** | JSON | IT solutions repository |
| **Logging** | Python logging module | Observability |
| **CLI** | argparse + asyncio | User interface |

---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.10+** (3.10.12 recommended)
- **Google API Key** (get from [Google AI Studio](https://aistudio.google.com/apikey))
- **Git** (for cloning the repository)

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/SupportPilot.git
cd SupportPilot
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
GOOGLE_API_KEY=your_api_key_here
```

**⚠️ IMPORTANT:** Never commit your `.env` file to Git!

### Step 5: Initialize Data Layer

This creates the knowledge base and ticket database:

```bash
python setup_data.py
```

Expected output:
```
✅ [OK] Knowledge Base created/reset: data/knowledge_base.json
✅ [OK] Ticket Database created: data/tickets.db
✅ [OK] Deleted Session Memory: data/sessions.db
```

### Step 6: Run the Application

```bash
# As end user (default)
python main.py --user_id alice_123

# As service desk agent
python main.py --user_id john_support --role service_desk_agent

# Guest mode (prompts for user_id)
python main.py
```

---

## 📖 Usage Guide

### Example Session (End User)

```
🤖 SupportPilot: 👋 Hello alice_123! Creating your profile...
🔐 Role: End User

👤 alice_123 > my printer is not printing

🤖 SupportPilot: I found a solution! Here's what to try:
1. Check if the printer is turned on and connected to the network.
2. Restart the printer.
3. Clear the print queue on your computer.
4. Check for paper jams.

Let me know if this resolves the issue!

👤 alice_123 > it didn't work

🤖 SupportPilot: I'm sorry to hear that. Would you like me to create a support ticket 
for our technicians to investigate further?

👤 alice_123 > yes please

🤖 SupportPilot: I've created Ticket #5 for your printer issue. 
Our Level 2 technicians will review it shortly.

👤 alice_123 > show my tickets

🤖 SupportPilot: You have 1 ticket:
- Ticket #5: Open (Issue: Printer not printing)
```

### Example Session (Service Desk Agent)

```
🤖 SupportPilot: 👋 Welcome back, john_support! (New Session Started)
🔐 Role: Service Desk Agent

👤 john_support > list all tickets

🤖 SupportPilot: Found 5 ticket(s):
- Ticket #1 (User: alice_123): Open - Normal priority (Issue: Printer not printing)
- Ticket #2 (User: bob_456): In Progress - High priority (Issue: VPN failed)
- Ticket #3 (User: alice_123): Closed - Low priority (Issue: Password reset)
[...]

👤 john_support > what is the status of ticket 1?

🤖 SupportPilot: Ticket #1 (User: alice_123): Open
Issue: Printer not printing
Priority: Normal
Created: 2025-01-15 10:30:00

👤 john_support > mark ticket 1 as in progress

🤖 SupportPilot: Success: Ticket #1 status updated to 'In Progress'.

👤 john_support > close ticket 1

🤖 SupportPilot: Ticket #1 has been closed successfully.
```

### Commands

| Command | Description |
|---------|-------------|
| `quit`, `exit`, `bye` | Exit the application |
| Technical question | Routes to Knowledge Agent |
| "create ticket..." | Routes to Ticket Agent |
| "show my tickets" | Lists user's tickets |
| "what is ticket X?" | Gets specific ticket details |
| "close ticket X" | Updates ticket status (service_desk only) |
| "who am I?" | Shows current user info |

---

## 📁 Project Structure

```
SupportPilot/
├── data/                          # Data storage
│   ├── knowledge_base.json       # IT solutions (seed data)
│   ├── tickets.db                # Ticket database (generated)
│   └── sessions.db               # Session memory (generated)
├── logs/                          # Observability
│   └── support_pilot.log         # Structured logs
├── src/                           # Source code
│   ├── __init__.py
│   ├── agents/                   # LLM Agents
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Main coordinator
│   │   ├── knowledge_agent.py   # KB search specialist
│   │   └── ticket_agent.py      # Ticket operations specialist
│   ├── tools/                    # Custom Tools
│   │   ├── __init__.py
│   │   ├── ticket_tools.py      # 4 ticket CRUD tools
│   │   ├── kb_tools.py          # KB search tool
│   │   └── session_tools.py     # Identity management
│   └── utils/                    # Utilities
│       ├── __init__.py
│       ├── logger.py            # Structured logging
│       ├── config.py            # Environment config
│       └── test_helpers.py      # Testing utilities
├── .env                          # API keys (DO NOT COMMIT)
├── .gitignore                    # Git ignore rules
├── main.py                       # CLI entry point
├── setup_data.py                 # Data initialization
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 🎓 ADK Concepts Demonstrated

This project implements **6 key concepts** from the Google ADK course:

### ✅ 1. Multi-Agent System
- **Sequential agents**: Orchestrator → Knowledge/Ticket agents
- **AgentTool pattern**: Sub-agents wrapped as tools
- **Clear separation of concerns**: Each agent has a single responsibility

### ✅ 2. Custom Tools
- **4 ticket tools**: create, get_by_id, list, update
- **1 KB tool**: search_knowledge_base
- **1 session tool**: get_my_info
- **All tools return dictionaries** (ADK best practice)

### ✅ 3. Sessions & Memory
- **DatabaseSessionService**: Long-term persistence
- **State management**: User identity and role stored in session
- **Conversation history**: Maintained across sessions

### ✅ 4. Observability: Logging
- **Structured logs**: Timestamp, level, module, message
- **Event tracking**: USER_INPUT, TOOL_CALL, TOOL_OUTPUT, AGENT_RESPONSE
- **File output**: `logs/support_pilot.log`

### ✅ 5. Role-Based Access Control (Enterprise Feature)
- **Two roles**: end_user, service_desk_agent
- **RBAC enforced** at tool level (invisible to agents)
- **Security**: Prevents privilege escalation

### ✅ 6. Context Engineering
- **Session state**: Persistent user identity
- **Conversation flow**: Agents maintain context across turns

---

## 🔮 Future Enhancements

Potential improvements for production deployment:

- [ ] **RAG Integration**: Replace JSON KB with vector database (e.g., Chroma, Pinecone)
- [ ] **Web UI**: React/Streamlit interface instead of CLI
- [ ] **MCP Integration**: Connect to real enterprise systems (Jira, ServiceNow)
- [ ] **Metrics Dashboard**: Real-time monitoring with Prometheus/Grafana
- [ ] **Agent Evaluation**: Implement LLM-as-a-Judge for quality scoring
- [ ] **A2A Protocol**: Multi-agent collaboration for complex workflows
- [ ] **Deployment**: Containerize with Docker, deploy to Vertex AI
- [ ] **Authentication**: Integrate with SSO (OAuth2, SAML)

---

## 🤝 Contributing

This project was developed as a capstone for the Kaggle course 5-Day Agents Intensive Course with Google. Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## 🙏 Acknowledgments

- **Google ADK Team**: For the excellent Agent Development Kit framework
- **Kaggle**: For hosting the 5-Day Agents Intensive Course with Google
- **Community**: For valuable feedback and testing

---

## 📧 Contact

**Project Link**: [https://github.com/jose-cachucho/SupportPilot](https://github.com/jose-cachucho/SupportPilot)

**Author**: José Cachucho

---

<div align="center">

**Built with ❤️ using Google ADK**

⭐ If you find this project useful, please consider giving it a star!

</div>