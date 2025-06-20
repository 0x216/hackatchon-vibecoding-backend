# Legal RAG Agent - Web Interface

🚀 **Beautiful and functional web interface for testing Legal RAG Agent**

## What is this?

Modern web interface for legal AI assistant that allows you to:
- 📄 Upload legal documents (PDF, DOCX, TXT)
- 💬 Ask questions about documents in chat
- 🤖 Get answers from AI (Groq, OpenAI)
- 📊 View response sources and metadata

## Quick Start

### 1. Run full stack
```bash
# Launch with frontend and all services
docker-compose -f docker-compose.frontend.yml up --build
```

### 2. Open browser
```
http://localhost:8000
```

### 3. Done! 🎉
- Upload demo document: `app/static/demo.txt`
- Ask question: "What salary is specified in the contract?"
- Get AI response!

## What's included

### 🎨 **Modern UI**
- Responsive design for all devices
- Drag & drop file upload
- Live AI chat
- Toast notifications
- Beautiful animations

### 🧠 **AI Integration**
- **Groq API** - fast responses
- **OpenAI** - high quality  
- **Mock mode** - for testing

### 📁 **Document Management**
- File upload
- Document list
- Processing status
- Active document selection

### 💬 **Chat Features**
- Message history
- Quick questions
- Response sources
- Metadata (model, tokens)

## API Endpoints

Frontend uses following APIs:

```javascript
// Document upload
POST /api/v1/documents/upload

// Document list  
GET /api/v1/documents/

// Chat with AI
POST /api/v1/chat/query

// Health check
GET /health
```

## File Structure

```
app/static/
├── index.html      # Main page
├── styles.css      # Interface styles
├── script.js       # JavaScript logic
└── demo.txt        # Demo document
```

## Features

### 🔥 **Quick Start**
- Automatic initialization
- API status check
- Document loading on startup

### 💡 **Smart Hints**
- Quick question buttons
- Auto-completion
- Contextual help

### 📱 **Responsive**
- Works on mobile
- Tablet optimization
- Desktop interface

## Demo Mode

For quick testing without document upload:

```javascript
// In browser console
enableDemoMode()
```

## Settings

### Change LLM Provider
Use selector in top right corner:
- **Groq** - fast and free
- **OpenAI** - high quality
- **Mock** - for development

### Environment Variables
```env
GROQ_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
DEBUG=true
```

## Troubleshooting

### Issue: API unavailable
**Solution:** Check status in top right corner
```bash
curl http://localhost:8000/health
```

### Issue: Upload not working
**Solution:** Check file format (PDF, DOCX, TXT)

### Issue: AI not responding
**Solution:** Check Groq API key in settings

## Technologies

- **Frontend**: Vanilla JS + CSS Grid + Flexbox
- **Backend**: FastAPI + SQLAlchemy + Async
- **AI**: Groq API + OpenAI API
- **Database**: PostgreSQL + pgvector
- **Vector DB**: Weaviate
- **Cache**: Redis

---

🎯 **Ready to use! Enjoy testing Legal RAG Agent!** 