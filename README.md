# TestProbe AI — Game Testing Platform

![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask)
![Selenium](https://img.shields.io/badge/Selenium-4.15-43b02a?style=flat-square&logo=selenium)
![Groq AI](https://img.shields.io/badge/Groq-AI-f55036?style=flat-square)

AI-powered web game testing platform that analyzes any web game from a URL, detects the game type, and determines whether the gameplay looks Human or AI-driven.

**Live Demo:** [game-tester-ai.onrender.com](https://game-tester-ai.onrender.com)

---

## Features

- Analyzes any web game from just a URL
- Uses Selenium to automatically play and test the game
- Detects game type (Puzzle, Racing, Endless Runner, etc.)
- Human vs AI gameplay detection using behavioral signals
- Chatbot interface to ask follow-up questions about the analysis
- Live dashboard with charts and metrics

---

## How It Works

1. User pastes a game URL
2. Selenium opens headless Chrome and loads the page
3. AI plays the game via keyboard simulation, collecting metrics (time survived, actions, score progression, errors)
4. Game type is classified (10 categories)
5. Human vs AI verdict is computed from 6 behavioral signals
6. Groq AI generates a natural-language analysis
7. Results are shown in chat + dashboard, and the user can ask follow-up questions

---

## Human vs AI Detection

| Signal | Human | AI/Bot |
|---|---|---|
| Action Rate | 0.3–2.0 actions/sec (variable) | >3.0 APS or perfectly consistent |
| Errors | 1–3 natural mistakes | Zero errors, or too many random ones |
| Score Progression | Variable, shows a learning curve | Too linear or completely flat |
| Session Duration | 15–60 seconds | Unnaturally short or long |
| Performance | Usually Medium/Low | Suspiciously High |
| Game-Type Behavior | Matches expected pace | Wrong pace for game type |

Verdict is generated using Groq AI (`llama-3.1-8b-instant`).

---

## Local Setup

### Prerequisites
- Python 3.11+
- Google Chrome
- Groq API key ([console.groq.com](https://console.groq.com))

### Installation

```bash
git clone https://github.com/Priyal9497/game-tester-ai.git
cd game-tester-ai

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
FLASK_DEBUG=true
PORT=5000
SECRET_KEY=your-secret-key-here
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.1-8b-instant
HEADLESS=false
```

Run the app:

```bash
python app.py
```

Then open `http://localhost:5000`.

---

## Project Structure

```
P_AI/
│
├── app.py      # Flask application & routes
├── chatbot.py  # Message processor & session management
├── tester.py   # Selenium game testing engine
├── ai_helper.py # Groq AI integration
│
├── requirements.txt # Python dependencies
├── Procfile    # Deployment config
├── build.sh    # Build script
├── Dockerfile  # Docker container config
├── .dockerignore # Docker ignore rules
├── render.yml  # Render deployment config
├── .gitignore  # Git ignore rules
├── .env        # Environment variables (not in git)
│
├── templates/
│ └── index.html # Frontend UI
│
├── static/
│ ├── css/
│ │ └── style.css # Stylesheet
│ └── js/
│ └── script.js  # Frontend logic
│
├── logs/        # Auto-created log files
├── pycache/     # Python cache (auto-generated)
└── venv/        # Virtual environment (not in git)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Browser Automation | Selenium WebDriver |
| AI/LLM | Groq API (Llama 3.1 8B) |
| Frontend | HTML5, CSS3, Vanilla JS, Chart.js |
| Deployment | Render |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Main UI |
| POST | `/test` | Analyze game URL or chat |
| GET | `/history` | Get test history |
| GET | `/current-game` | Current game context |
| GET | `/health` | Health check |

**Example — POST `/test`**

Request:
```json
{ "message": "https://chromedino.com" }
```

Response:
```json
{
  "type": "test_result",
  "reply": "TEST COMPLETE! ...",
  "metrics": {
    "time_survived": 25.3,
    "actions": 10,
    "performance": "Medium",
    "scores": [0, 12, 24, 36],
    "errors": 1,
    "game_type": {
      "primary_type": "Endless Runner",
      "confidence": "High"
    }
  },
  "human_verdict": {
    "verdict": "AI/Bot",
    "confidence": "High",
    "reason": "Consistent action rate detected"
  }
}
```

---

## Security

- URL validation and domain blacklist
- Rate limiting (50 requests/hour)
- Session-based conversation tracking
- Input sanitization, no sensitive data in responses

---

## Limitations

- Free Render tier may sleep after 15 min of inactivity (first request takes 30–60s to wake)
- Some sites block headless Chrome
- Login-gated or Flash-only games are not supported

---

## Contributing

```bash
git checkout -b feature/amazing-feature
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

Then open a Pull Request.

---

## License

MIT License — free to use and modify.

## Author

**Priyal** — [GitHub](https://github.com/Priyal9497) · [Project](https://github.com/Priyal9497/game-tester-ai) · [Live Demo](https://game-tester-ai.onrender.com)
