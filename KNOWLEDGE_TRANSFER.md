# DerivInsight NL2SQL - Knowledge Transfer Document

## 🎯 Project Overview

**DerivInsight** is an AI-powered Natural Language to SQL (NL2SQL) platform with autonomous security monitoring capabilities. The system transforms natural language queries into SQL, executes them, and provides AI-driven insights with visualizations.

### Key Innovation: Sentinel Mode
The platform features a **Sentinel Agent** - an autonomous AI service that proactively monitors database security, compliance, risk, and operations without human intervention.

---

## 🏗️ Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vanilla JS)                     │
│  - Chat Interface (Reactive Mode)                            │
│  - Sentinel Dashboard (Proactive Mode)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         LangGraph Orchestration Workflow              │   │
│  │  Intent → SQL Gen → Validation → Execution → Insights│   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Sentinel Brainstorming Agent                  │   │
│  │  Autonomous mission generation & execution            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Database Layer (SQLite/PostgreSQL)              │
│  - users, transactions, login_events                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
nl2sql/
├── app/
│   ├── api/                      # API Endpoints
│   │   ├── endpoints.py          # Main NL2SQL query endpoint
│   │   ├── sentinel.py           # Autonomous Sentinel scan endpoint
│   │   ├── alerts_endpoints.py   # Alert management
│   │   └── dashboard_endpoints.py
│   │
│   ├── orchestration/            # Core AI Workflows
│   │   ├── workflow.py           # LangGraph NL2SQL pipeline
│   │   └── sentinel_agent.py     # Autonomous brainstorming agent
│   │
│   ├── modules/                  # NL2SQL Pipeline Modules
│   │   ├── intent_classification.py
│   │   ├── sql_generation.py
│   │   ├── validation.py
│   │   ├── visualization.py
│   │   └── insight_generation.py
│   │
│   ├── data/domains/             # Domain-Specific Configurations
│   │   ├── general.json
│   │   ├── security.json
│   │   ├── compliance.json
│   │   ├── risk.json
│   │   └── operations.json
│   │
│   ├── models/                   # Pydantic Models
│   │   └── state.py              # GraphState, QueryRequest, QueryResponse
│   │
│   ├── services/                 # Core Services
│   │   ├── database.py           # Database execution
│   │   └── llm.py                # LLM interaction wrapper
│   │
│   └── core/                     # Configuration & Utilities
│       ├── config.py             # Settings (API keys, DB, Redis)
│       └── logger.py
│
├── frontend/                     # Frontend Application
│   ├── index.html                # Main HTML (Sentinel + Chat)
│   ├── script.js                 # Frontend logic
│   └── styles.css                # Glassmorphism UI styles
│
├── .env                          # Environment variables
├── requirements.txt              # Python dependencies
└── derivinsightnew.db            # SQLite database
```

---

## 🔑 Key Features

### 1. **Reactive Mode (Chat Interface)**
- User asks natural language questions
- AI classifies intent and generates SQL
- Results displayed with AI insights and visualizations
- Supports clarification flow for ambiguous queries

### 2. **Proactive Mode (Sentinel Dashboard)**
- **Autonomous Agent** brainstorms security/compliance missions
- Generates dynamic audit questions based on schema
- Executes missions across 3 domains:
  - 🛡️ **Security & Risk**
  - 📜 **Compliance**
  - 📈 **Operations**
- Displays live detections with mini-charts and protocol recommendations

### 3. **Domain-Specific Intelligence**
Each domain has custom:
- Schema context
- SQL generation rules
- Few-shot examples
- Intent classification prompts

### 4. **LangGraph Workflow Pipeline**
```
User Query → Intent Classification → SQL Generation → Validation
    ↓
Repair Loop (if invalid) → Execute Query → Parallel:
    ├─ Visualization Recommendation
    └─ Insight & Recommendation Generation
```

---

## 🧠 Core Technologies

### Backend
- **FastAPI**: REST API framework
- **LangGraph**: Agentic workflow orchestration
- **LangChain**: LLM integration (Google Gemini)
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation

### Frontend
- **Vanilla JavaScript**: No framework dependencies
- **Chart.js**: Data visualizations
- **Marked.js**: Markdown rendering

### AI/LLM
- **Google Gemini**: Primary LLM (gemini-2.5-flash-lite)
- **Temperature 0.0**: SQL generation (deterministic)
- **Temperature 0.8**: Sentinel brainstorming (creative)

### Database
- **SQLite**: Development/Demo
- **PostgreSQL**: Production-ready (configurable)

---

## 🚀 Current Focus Areas

### 1. **Sentinel Agent Enhancement** (PRIORITY)
**Location**: `app/orchestration/sentinel_agent.py`

**What it does**:
- Dynamically generates audit missions using LLM
- Knows database schema and business context
- Creates sophisticated questions for each domain

**Current Implementation**:
```python
class SentinelBrainstormer:
    async def brainstorm_missions(self, count_per_domain=2):
        # Uses Gemini to generate dynamic audit questions
        # Returns JSON list of missions with:
        # - id, name, query, domain, severity
```

**Next Steps**:
- Add mission history tracking (avoid repetition)
- Implement priority scoring based on data patterns
- Add scheduled scans (cron-like)

### 2. **Visualization Intelligence**
**Location**: `app/modules/visualization.py`

**Current State**:
- AI recommends chart types (bar, line, pie, etc.)
- Identifies X/Y axes from query results
- Supports mini-charts in Sentinel cards

**Enhancement Needed**:
- Better handling of time-series data
- Multi-dataset visualizations
- Interactive drill-down capabilities

### 3. **Domain Configuration Sync**
**Location**: `app/data/domains/*.json`

**Critical Rules**:
- Email data is in `login_events.email_attempted` (NOT in users table)
- Risk scores range 0-100 (use `> 70` for "high risk")
- Geographical data requires JOIN with `login_events`

**Recent Updates**:
- All domains now correctly map email fields
- Added risk score calibration rules
- Enhanced few-shot examples

---

## 🔧 Environment Setup

### Required Environment Variables (.env)
```bash
# LLM Configuration
GEMINI_API_KEY=your_api_key_here
INTENT_MODEL=gemini-2.5-flash-lite
SQL_MODEL=gemini-2.5-flash-lite

# Database
DATABASE_URL=sqlite:///./derivinsightnew.db

# Redis/Valkey (Optional - for caching)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_USE_SSL=true
```

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run backend
python -m uvicorn app.main:app --reload --port 8080

# Run frontend (separate terminal)
python -m http.server 8081 --directory frontend
```

### Access
- **Frontend**: http://localhost:8081
- **API Docs**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

---

## 📊 Database Schema

### Tables
```sql
-- Users table
users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    age INTEGER,
    kyc_status TEXT,
    risk_level TEXT,
    risk_score REAL,
    is_pep BOOLEAN,
    account_status TEXT
)

-- Transactions table
transactions (
    txn_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    txn_type TEXT,
    instrument TEXT,
    amount REAL,
    currency TEXT,
    amount_usd REAL,
    status TEXT,
    flag_reason TEXT,
    payment_method TEXT
)

-- Login Events table
login_events (
    event_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    email_attempted TEXT,  -- ⚠️ EMAIL IS HERE, NOT IN USERS
    status TEXT,
    country TEXT,
    city TEXT,
    device_type TEXT,
    failure_reason TEXT
)
```

---

## 🎨 Frontend Architecture

### Two Modes

#### 1. Chat Mode (Hidden by default)
- Traditional Q&A interface
- User types natural language queries
- Shows SQL, results, insights, and charts

#### 2. Sentinel Mode (Default)
- 3-column grid layout:
  - Security & Risk
  - Compliance
  - Operations
- Auto-populates with AI-generated detections
- Each card shows:
  - Mission name
  - Severity badge
  - Mini-chart (if applicable)
  - AI insight
  - Protocol recommendation

### Toggle Between Modes
```javascript
// User clicks "SENTINEL MODE" or "QUERY CHAT" button
async function toggleSentinelMode() {
    state.isSentinelMode = !state.isSentinelMode;
    // Show/hide appropriate containers
}
```

---

## 🔐 Security Considerations

### Current Implementation
- No authentication (demo mode)
- SQL injection prevention via parameterized queries
- Input validation through Pydantic models

### Production Requirements
- Add JWT authentication
- Implement role-based access control (RBAC)
- Rate limiting on API endpoints
- Audit logging for all queries

---

## 🐛 Known Issues & Limitations

### 1. **Sentinel Agent Hallucination**
- **Issue**: Agent may generate missions for non-existent columns
- **Mitigation**: Schema validation in brainstorming prompt
- **Future**: Add schema introspection before mission execution

### 2. **Visualization Edge Cases**
- **Issue**: Some queries don't have suitable chart types
- **Current**: Falls back to table view
- **Future**: Better heuristics for chart selection

### 3. **Redis Connection**
- **Status**: Falls back to SQLite if Redis unavailable
- **Impact**: No distributed caching
- **Fix**: Ensure Redis/Valkey is properly configured

---

## 📈 Performance Metrics

### Current Benchmarks
- **Intent Classification**: ~500ms
- **SQL Generation**: ~800ms
- **Query Execution**: <100ms (SQLite)
- **Insight Generation**: ~600ms
- **Total E2E**: ~2-3 seconds

### Optimization Opportunities
- Parallel LLM calls (already implemented for viz + insights)
- Response streaming for large results
- Query result caching in Redis

---

## 🧪 Testing Strategy

### Current Coverage
- Manual testing via frontend
- API endpoint testing via `/docs`

### Recommended Additions
```bash
# Unit tests
tests/test_intent_classification.py
tests/test_sql_generation.py
tests/test_validation.py

# Integration tests
tests/test_workflow.py
tests/test_sentinel_agent.py

# E2E tests
tests/test_api_endpoints.py
```

---

## 🚢 Deployment

### Current Setup
- Local development only
- SQLite database (file-based)

### Production Checklist
- [ ] Switch to PostgreSQL
- [ ] Configure Redis/Valkey for caching
- [ ] Set up proper logging (CloudWatch, etc.)
- [ ] Add monitoring (Prometheus, Grafana)
- [ ] Configure CORS properly
- [ ] Set up CI/CD pipeline
- [ ] Docker containerization
- [ ] Environment-specific configs

---

## 📚 Key API Endpoints

### 1. NL2SQL Query
```http
POST /api/v1/query
Content-Type: application/json

{
  "query": "Show me high risk users",
  "domain": "security",
  "conversation_history": []
}
```

### 2. Sentinel Scan
```http
GET /api/v1/sentinel/scan

Response:
{
  "status": "success",
  "detections": [
    {
      "mission_id": "sec-001",
      "mission_name": "AML Velocity Watch",
      "domain": "security",
      "severity": "CRITICAL",
      "sql": "SELECT ...",
      "insight": "AI-generated insight",
      "recommendation": "Protocol recommendation",
      "visualization_config": {...}
    }
  ]
}
```

---

## 🎓 Learning Resources

### For New Developers
1. **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
2. **FastAPI Tutorial**: https://fastapi.tiangolo.com/tutorial/
3. **Pydantic Guide**: https://docs.pydantic.dev/

### Project-Specific
- Review `app/orchestration/workflow.py` for workflow logic
- Study `app/data/domains/security.json` for domain config format
- Check `frontend/script.js` for Sentinel rendering logic

---

## 🤝 Contributing Guidelines

### Code Style
- Python: Follow PEP 8
- JavaScript: Use ES6+ features
- Comments: Explain "why", not "what"

### Git Workflow
```bash
# Feature branch
git checkout -b feature/sentinel-history-tracking

# Commit with descriptive messages
git commit -m "feat: Add mission history tracking to Sentinel Agent"

# Push and create PR
git push origin feature/sentinel-history-tracking
```

---

## 📞 Support & Contact

### Key Files to Reference
- **Workflow Issues**: `app/orchestration/workflow.py`
- **Sentinel Issues**: `app/orchestration/sentinel_agent.py`
- **Frontend Issues**: `frontend/script.js`
- **Config Issues**: `app/core/config.py`

### Debugging Tips
1. Check logs in `logs/app.log`
2. Use `/docs` for API testing
3. Enable debug mode: `LOG_LEVEL=DEBUG` in `.env`
4. Test LLM prompts in isolation before integrating

---

## 🎯 Immediate Next Steps for New Developer

1. **Day 1**: Set up environment, run locally, explore both modes
2. **Day 2**: Review LangGraph workflow, understand state flow
3. **Day 3**: Study Sentinel Agent brainstorming logic
4. **Day 4**: Make a small enhancement (e.g., add new domain)
5. **Day 5**: Review domain configs and add few-shot examples

---

**Last Updated**: 2026-02-07  
**Version**: 1.0  
**Maintainer**: Development Team
