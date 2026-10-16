# CivicSathi AI

**AI for Digital Public Infrastructure of Chandigarh · Civic Services**

CivicSathi AI is a prototype concept for helping residents navigate civic services and prepare clearer complaints. It is designed as an assistance layer—not a replacement for the official I’m Chandigarh or Municipal Corporation Chandigarh systems.

> **Prototype status:** This repository is a starter implementation. It does not connect to live municipal systems, submit real complaints, or represent an official government integration. Do not enter sensitive personal information.

## Current capabilities

- A Streamlit web interface for a resident's civic request.
- Open-weight model access through a locally running Ollama server.
- A model harness that loads the `civic-request-intake` Agent Skill, validates structured output, and restricts consequential actions.
- Basic similarity hints against sample complaints for human review.
- Local, minimal audit events and starter automated tests.

## Requirements

- Python 3.10+
- Git
- Optional for real model inference: [Ollama](https://ollama.com/) and a compatible local model. Default: `qwen2.5:3b` (model availability/license must be checked for your use case).
- For one-command publication: [GitHub CLI](https://cli.github.com/) installed and authenticated with `gh auth login`.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For open-weight AI, install and start Ollama, then pull a model:

```powershell
ollama pull qwen2.5:3b
```

Run the prototype:

```powershell
streamlit run app.py
```

Configure another compatible Ollama model with `$env:OLLAMA_MODEL="your-model-name"` before launching.

If Ollama is not reachable, the app reports that model inference is unavailable; it does not pretend a rule-based result is AI-generated.

## Tests

```powershell
python -m pytest
```

## Publish to a new public GitHub repository

1. Install Git and GitHub CLI.
2. Run `gh auth login` and finish authentication in your browser.
3. Open PowerShell in this folder and run:

```powershell
.\publish.ps1
```

The script creates `civicsathi-ai` as a public GitHub repository, initializes Git, commits the starter files, and pushes them. If you want a different repository name, run `./publish.ps1 -RepoName your-repo-name`.

## Safety and limitations

- AI output is an untrusted draft; the resident must review it.
- Duplicate detection only suggests possible matches; it never rejects a complaint.
- No live municipal APIs, resident records, payments, complaint submission, or case closure are connected.
- Use public, verified sources when adding service guidance. Keep secrets and personal information out of Git history.

## Project status

Starter scaffold for a hackathon proposal. Features and evaluation results must be verified and updated as they are implemented. Do not claim measured accuracy or live integrations without evidence.

## License

Apache-2.0. See `LICENSE`.
