# 🦅 InsightOS: The Virtual CIO for Real-Time Financial Intelligence

[![Demo Verification](https://img.shields.io/badge/Demo-Verified_100%25-brightgreen.svg)]()
[![Orchestration](https://img.shields.io/badge/Orchestration-LangGraph-blue.svg)]()
[![Intelligence](https://img.shields.io/badge/Engine-Gemini_2.5_Flash-orange.svg)]()

> **InsightOS** transforms complex natural language into actionable executive-level business intelligence. It’s not just an NL2SQL tool; it’s an AI-driven decision engine that reasons across your entire database to provide strategic recommendations.

---

## 🏗️ System Architecture

Our engine utilizes a **Multi-Agent Orchestration Flow** powered by **LangGraph**. This architecture decouples intent classification, schema reasoning, and executive synthesis into a high-precision pipeline.

```mermaid
flowchart TD
    %% User Entry
    User([Executive Query]) --> API[FastAPI Gateway]

    subgraph NL2SQL_Core ["NL2SQL Orchestration Pipeline (LangGraph)"]
        direction TB
        API --> Intent[Intent & Domain Classifier]
        Intent --> Router{Domain Specific?}
        
        Router -->|Operations| D1[Ops Context]
        Router -->|Risk| D2[Risk Context]
        Router -->|Security| D3[Security Context]
        Router -->|Compliance| D4[Compliance Context]
        
        D1 & D2 & D3 & D4 --> Retriever[Few-Shot & Schema Retriever]
        Retriever --> SQLGen[SQL Generation Agent]
        
        SQLGen --> Validator{SQL Validator}
        Validator -->|Pass| Exec[Secure DB Execution]
        Validator -->|Fail| Repair[Self-Repair Agent]
        Repair --> SQLGen
    end

    subgraph CIO_Reasoning ["The Virtual CIO Engine"]
        direction TB
        Exec --> Viz[Visual Preference Discovery]
        Viz --> Insight[Executive Insight Synthesis]
        Insight --> Recommendations[Actionable Strategy Generator]
    end

    %% Result Delivery
    Recommendations --> Dashboard([InsightOS Executive Briefing])
    Dashboard -.-> |Feedback Loop| User

    %% Styling
    style User fill:#f9f,stroke:#333,stroke-width:2px
    style Intent fill:#6b5b95,stroke:#fff,color:#fff
    style SQLGen fill:#f96,stroke:#333
    style Validator fill:#feb236,stroke:#333
    style Exec fill:#d64161,stroke:#fff,color:#fff
    style Dashboard fill:#3ff,stroke:#333,stroke-width:4px
    style Recommendations fill:#00d2ff,stroke:#333,stroke-width:2px
```

---

## 🛠️ Pipeline Breakdown

### 1. **Contextual Intent Layer**
Unlike generic NL2SQL, InsightOS understands the **Domain Context** (Risk vs. Ops). This allows the system to differentiate between "flagged" for a fraud reason and "flagged" for a transaction status error.

### 2. **Self-Healing SQL Agent**
The system implements a **Retry & Repair** loop. If the generated SQLite is syntactically correct but functionally fails execution, the error message is fed back to the Agent for an immediate "hot-fix."

### 3. **Executive Synthesis (The CIO)**
The final output is not a JSON blob. It is a synthesized report containing:
- **The Finding**: Direct answer to the query.
- **The Insight**: Root cause analysis or trend detection.
- **The Recommendation**: A suggested business action (e.g., "Adjust credit limits for High-Risk users").

---

## ✨ Key Features

*   **🛡️ Multi-Domain Intelligence**: Dedicated prompts for Operations, Risk, Compliance, and Security.
*   **📊 Dynamic Visualization**: Automatically chooses the best chart (Bar, Line, Pie, or Table) based on data distribution.
*   **⚡ Sub-Second Latency**: Optimized query generation using Gemini 2.5 Flash.
*   **🔌 Plug-and-Play**: Seamless integration with existing SQLite/SQLAlchemy databases.

---

## 🚀 Getting Started

### 1. Environment Setup
```bash
python -m venv venv
./venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file with your Google Gemini API Key:
```env
GOOGLE_API_KEY=your_gemini_key
DB_PATH=./derivinsightnew.db
```

### 3. Run the Platform
```bash
python -m uvicorn app.main:app --reload --port 8080
```

---

## 💎 Demo Verification (Try These)

| Domain | Executive Question | Impact |
| :--- | :--- | :--- |
| **Risk** | *"Show me all users and their risk levels."* | **Critical Profile Alert** |
| **Security**| *"Show me failed logins by reason and IP address."* | **Threat Intelligence** |
| **Growth** | *"Which countries have the highest active users?"* | **Market Optimization** |
| **Fraud** | *"List all transactions in 'FLAGGED' status."* | **AML Monitoring** |

---

Developed for the **Deriv Hackathon** – *Empowering Executives with Data-First Decisioning.*
