# 🚀 SupportPilot - Quick Setup Guide

## Prerequisites
- Python 3.9+
- Google AI API key ([Get one here](https://aistudio.google.com/app/apikey))

---

## Step-by-Step Setup

### 1. Create Virtual Environment
```bash
# Create venv
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
```bash
# Copy template
cp .env.example .env

# Edit .env and add your key
# GOOGLE_API_KEY=your-actual-api-key-here
```

**Or set directly:**
```bash
export GOOGLE_API_KEY='your-api-key-here'  # Linux/Mac
set GOOGLE_API_KEY=your-api-key-here       # Windows
```

### 4. Verify Setup
```bash
python test_setup.py
```

Expected output:
```
✓ Imports
✓ Environment  
✓ Database
✓ Tools
✓ Agent Initialization

✅ All tests passed! System is ready.
```

---

## Running SupportPilot

### Interactive Mode
```bash
python src/main.py
```

Example session:
```
👤 You: My VPN is not connecting
🤖 SupportPilot: I found a solution for this issue...
```

### Demo Mode (for Kaggle Video)
```bash
python src/main.py --demo
```

Runs 5 predefined scenarios showcasing all features.

---

## Troubleshooting

### ❌ "GOOGLE_API_KEY not found"
**Solution**: Make sure `.env` file exists and contains your key:
```bash
cat .env  # Should show: GOOGLE_API_KEY=...
```

### ❌ "ModuleNotFoundError: No module named 'google.adk'"
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### ❌ "sqlite3.OperationalError"
**Solution**: Delete and recreate database:
```bash
rm data/service_desk.db
python src/main.py  # Will auto-create
```

### ❌ Agent initialization fails
**Solution**: Check API key is valid at https://aistudio.google.com/app/apikey

---

## Project Structure
```
SupportPilot/
├── src/
│   ├── agents/          # 4 ADK agents
│   ├── tools/           # 3 custom tools
│   ├── core/            # Database + observability
│   ├── models/          # Session metadata
│   └── main.py          # CLI entry point
├── data/
│   ├── knowledge_base.json    # 20 IT articles
│   └── service_desk.db        # SQLite (auto-created)
├── test_setup.py        # Verification script
├── requirements.txt
└── .env                 # Your API key (create this)
```

---

## Next Steps

1. ✅ Run `test_setup.py` to verify everything works
2. ✅ Try interactive mode: `python src/main.py`
3. ✅ Record demo: `python src/main.py --demo`
4. ✅ Submit to Kaggle with video!

---

## Quick Test Commands

```bash
# Test single interaction
python src/main.py
> My VPN is not working

# Check metrics
python src/main.py
> /status

# Reset session
python src/main.py
> /reset
```

---

## Need Help?

- Check `README.md` for detailed documentation
- Run `test_setup.py` to diagnose issues
- Ensure Python 3.9+ is installed: `python --version`