# DerivInsight Frontend

A beautiful, modern web interface for testing the NL2SQL Pipeline with real-time chat and data visualization.

## ✨ Features

- 🎨 **Modern Dark UI** - Stunning glassmorphism design with smooth animations
- 💬 **Real-time Chat** - Conversational interface for natural language queries
- 📊 **Dynamic Charts** - Auto-generated visualizations using Chart.js
- 📋 **Data Tables** - Clean, responsive tables for query results
- 🔄 **Domain Selection** - Switch between security, compliance, risk, operations, and general domains
- 📥 **CSV Export** - Export query results to CSV files
- 🎯 **Quick Examples** - Pre-built example queries to get started quickly
- ⚡ **Live Connection Status** - Real-time API connectivity monitoring

## 🚀 Quick Start

### Option 1: Open Directly in Browser

1. Make sure your NL2SQL API server is running:
   ```bash
   cd c:\Users\josea\Desktop\nl2sql
   python app\main.py
   ```

2. Open the frontend:
   ```bash
   # On Windows, simply open the file
   start frontend\index.html
   ```

3. The frontend will automatically connect to `http://localhost:8080`

### Option 2: Serve with Python HTTP Server

For better CORS handling, you can serve the frontend through a simple HTTP server:

```bash
cd c:\Users\josea\Desktop\nl2sql\frontend
python -m http.server 8081
```

Then open: `http://localhost:8081`

### Option 3: Use FastAPI to Serve Frontend

Update your FastAPI app to serve static files (see below).

## 🔧 Configuration

### API Endpoint

By default, the frontend connects to `http://localhost:8000`. You can change this in the UI:

1. Look for the **API Configuration** section in the sidebar
2. Update the **API Endpoint** field
3. The connection status will update automatically

### Changing the Default URL

Edit `frontend/script.js` and update:

```javascript
const state = {
    apiUrl: 'http://your-api-url:port',
    // ... rest of config
};
```

## 📁 File Structure

```
frontend/
├── index.html          # Main HTML structure
├── styles.css          # Modern CSS with animations & responsive design
├── script.js           # Application logic & API integration
└── README.md          # This file
```

## 🎯 How to Use

### 1. Select a Domain
Choose from the domain buttons in the left sidebar:
- 🌐 General
- 🔒 Security
- 📋 Compliance
- ⚠️ Risk
- ⚙️ Operations

### 2. Ask a Question
Type your natural language query in the input box, for example:
- "Show me all high severity incidents"
- "What are the compliance violations in the last 30 days?"
- "List all open security risks"

### 3. View Results
- See the generated SQL in the chat
- View data in interactive tables
- Explore auto-generated charts (when applicable)
- Export results to CSV

### 4. Handle Clarifications
If the AI needs more information, it will ask clarifying questions. Simply respond in the chat.

## 🎨 Customization

### Colors
Edit `styles.css` to customize the color scheme:

```css
:root {
    --primary-500: #6366f1;    /* Primary color */
    --purple-500: #8b5cf6;     /* Secondary color */
    --bg-primary: #0a0a0f;     /* Background */
    /* ... more variables */
}
```

### Chart Types
By default, the app uses:
- Bar charts for ≤10 data points
- Line charts for >10 data points

Modify in `script.js` → `createChart()` function.

### Example Queries
Add your own examples in `index.html`:

```html
<div class="example-item" data-query="Your query here">
    <span class="example-icon">💡</span>
    Your Query Title
</div>
```

## 🔌 API Integration

The frontend expects these API endpoints:

### Health Check
```
GET /health
Response: { "status": "healthy" }
```

### Query Endpoint
```
POST /api/v1/query
Body: {
    "query": "string",
    "domain": "general|security|compliance|risk|operations",
    "conversation_id": "string",
    "conversation_history": []
}

Response: {
    "sql": "string",
    "results": [],
    "status": "success|failed|needs_clarification",
    "error": "string (optional)",
    "clarification_question": "string (optional)",
    "is_final": boolean
}
```

## 🐛 Troubleshooting

### "Disconnected" Status
- Make sure the API server is running on port 8000
- Check if the API URL in settings is correct
- Verify CORS is enabled on the API server

### Charts Not Showing
- Charts only appear for data with numeric columns
- Maximum 50 rows for auto-charting
- Need at least one numeric column

### CORS Issues
If opening `index.html` directly gives CORS errors, use one of these solutions:

1. **Use Python HTTP Server** (recommended):
   ```bash
   cd frontend
   python -m http.server 8080
   ```

2. **Enable CORS in FastAPI**:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

## 📊 Chart.js Integration

The frontend uses Chart.js 4.4.1 for visualizations. Charts are automatically generated when:
- Data has numeric columns
- Row count ≤ 50
- At least one label column exists

## 🌐 Browser Support

- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari
- ⚠️ IE 11 (not supported)

## 📝 License

This frontend is part of the DerivInsight NL2SQL Pipeline project.

## 🤝 Contributing

To improve the frontend:
1. Edit the files directly
2. Refresh your browser to see changes
3. No build process required!

## 📞 Support

For issues or questions:
- Check the browser console for errors
- Verify API connectivity
- Ensure all dependencies are loaded (Chart.js)

---

**Enjoy your AI-powered SQL queries! 🚀**
