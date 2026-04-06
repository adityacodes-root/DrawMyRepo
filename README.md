# DrawMyRepo

I built this project to help visualize the architecture of different GitHub repositories. You just paste a GitHub link, and it clones the repo locally, reads the files, and uses the Gemini API to draw a Mermaid diagram of how everything connects.

## Features

- **Auto-analyzes repos:** It downloads the repo and checks the folder structure and important config files (like `package.json` or `requirements.txt`).
- **AI diagrams:** Uses Gemini to figure out the architecture and generate a Mermaid diagram, along with a short explanation of how the repo works.
- **Different modes:** You can generate a basic diagram for beginners or a more technical one if you want to see all the backend details.
- **History & Caching:** Saves previous diagrams in a local SQLite database (`cache.db`) so it doesn't have to hit the API again for repos you've already checked.
- **Export options:** You can copy the raw Mermaid code or download the diagram as an SVG.
- **Diagram links:** If a component in the diagram maps to a specific file, you can click it to jump straight to that file on GitHub.

## What you need to run it
- Python 3.10+
- Git 
- A Google Gemini API Key

## How to set it up

1. **Set your API Key**
   You need to set your Gemini API key in your terminal before running the backend.
   ```bash
   # Windows (Command Prompt)
   set GEMINI_API_KEY=your_api_key_here
   
   # Windows (PowerShell)
   $env:GEMINI_API_KEY="your_api_key_here"
   
   # Mac/Linux
   export GEMINI_API_KEY="your_api_key_here"
   ```

2. **Install the backend stuff**
   Make sure you are in the project folder and run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the backend**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8010
   ```

4. **Open the frontend**
   You can just open `frontend/index.html` in your browser, or start a simple python server:
   ```bash
   cd frontend
   python -m http.server 8080
   ```
