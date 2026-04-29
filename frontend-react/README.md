# DerivInsight React Frontend

Modern, professional React-based frontend for the DerivInsight NL2SQL platform.

## 🚀 Features

### Dual-Mode Interface
- **Chat Mode**: Interactive natural language query interface
- **Sentinel Mode**: Autonomous AI monitoring dashboard

### Modern Tech Stack
- ⚛️ **React 18** with TypeScript
- ⚡ **Vite** for blazing-fast development
- 🔄 **React Query** for efficient data fetching
- 📊 **Chart.js** for beautiful visualizations
- 🎨 **Glassmorphism UI** with premium animations

## 📦 Installation

```bash
cd frontend-react
npm install
```

## 🏃 Running the App

```bash
# Development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🏗️ Project Structure

```
frontend-react/
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx          # Mode toggle & domain selection
│   │   ├── ChatInterface.tsx    # NL2SQL chat interface
│   │   └── SentinelDashboard.tsx # Autonomous monitoring
│   ├── App.tsx                  # Main app component
│   ├── main.tsx                 # Entry point
│   └── index.css                # Global styles
├── package.json
└── vite.config.ts               # Vite configuration
```

## 🎨 Key Components

### Sidebar
- Mode switching (Chat ↔ Sentinel)
- Domain selection (General, Security, Compliance, Risk, Operations)
- Quick example queries
- API configuration display

### Chat Interface
- Natural language input
- Real-time query processing
- SQL display with copy functionality
- Interactive charts (Bar, Line, Pie)
- Results table
- AI insights and recommendations
- Conversation history

### Sentinel Dashboard
- 3-column grid layout (Security & Risk, Compliance, Operations)
- Live AI-generated detections
- Mini-charts for quick data visualization
- Severity-coded alerts (Critical, High, Medium)
- Auto-refresh capability
- Protocol recommendations

## 🔌 API Integration

The frontend connects to the FastAPI backend at `http://localhost:8080`.

### Endpoints Used
- `POST /api/v1/query` - NL2SQL query execution
- `GET /api/v1/sentinel/scan` - Autonomous security scan
- `GET /health` - Health check

## 🎨 Design System

### Color Palette
- **Primary Background**: `#0f172a` (Dark Blue)
- **Secondary Background**: `#1e293b` (Slate)
- **Accent**: `#6366f1` (Indigo)
- **Success**: `#10b981` (Green)
- **Warning**: `#f59e0b` (Amber)
- **Danger**: `#ef4444` (Red)

### Typography
- **Font Family**: Inter (Google Fonts)
- **Weights**: 300-900

### Effects
- Glassmorphism backgrounds
- Smooth transitions and animations
- Pulse effects for live indicators
- Hover states with elevation

## 🔧 Configuration

### Vite Proxy
API requests are proxied through Vite to avoid CORS issues:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
    },
  },
}
```

## 📱 Responsive Design

The interface is fully responsive and works on:
- Desktop (1920px+)
- Laptop (1200px+)
- Tablet (768px+)
- Mobile (320px+)

## 🚀 Performance

- **Code Splitting**: Automatic with Vite
- **Tree Shaking**: Enabled by default
- **Hot Module Replacement**: Instant updates during development
- **Optimized Bundle**: Production builds are minified and optimized

## 🎯 User Flow

### Chat Mode
1. User selects domain (e.g., Security)
2. Types natural language query
3. AI generates SQL and executes
4. Results displayed with:
   - SQL code
   - Data table
   - Visualization (if applicable)
   - AI insights
   - Recommendations

### Sentinel Mode
1. User clicks "Sentinel Mode" button
2. Dashboard loads with 3 columns
3. Click "Refresh Scan" to trigger autonomous audit
4. AI brainstorms missions across domains
5. Executes missions in parallel
6. Displays live detections with:
   - Severity badges
   - Mini-charts
   - Insights
   - Protocol recommendations

## 🔐 Security

- No sensitive data stored in frontend
- API keys managed on backend
- CORS handled via Vite proxy
- Input sanitization through React

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5173
npx kill-port 5173

# Or use a different port
npm run dev -- --port 3000
```

### API Connection Failed
- Ensure backend is running on `http://localhost:8080`
- Check `/health` endpoint
- Verify CORS settings in backend

### Build Errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 📊 Dependencies

### Core
- `react` - UI library
- `react-dom` - DOM rendering
- `typescript` - Type safety

### Data Fetching
- `@tanstack/react-query` - Server state management

### UI/UX
- `react-hot-toast` - Toast notifications
- `react-markdown` - Markdown rendering
- `chart.js` - Charts
- `react-chartjs-2` - React wrapper for Chart.js

### Build Tools
- `vite` - Build tool
- `@vitejs/plugin-react` - React plugin for Vite

## 🎓 Development Tips

### Adding New Components
```tsx
// Create component file
src/components/MyComponent.tsx

// Import in App.tsx
import MyComponent from './components/MyComponent';
```

### Styling
- Use CSS modules or inline styles
- Follow existing color variables
- Maintain glassmorphism aesthetic

### State Management
- Use React Query for server state
- Use useState for local UI state
- Avoid prop drilling with context if needed

## 🚀 Deployment

### Build for Production
```bash
npm run build
```

Output will be in `dist/` directory.

### Deploy to Vercel/Netlify
1. Connect GitHub repository
2. Set build command: `npm run build`
3. Set output directory: `dist`
4. Add environment variables if needed

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]
```

## 📝 License

Part of the DerivInsight NL2SQL project.

---

**Built with ❤️ using React + Vite + TypeScript**
