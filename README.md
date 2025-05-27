# Japanese Kanji Learning Assistant

This is a prototype assistant for learning Japanese kanji, designed to supplement [WaniKani](https://wanikani.com).
The code gets a list of kanji vocabulary up to and including your current WaniKani level and generates conversations based around that vocabulary.

## Installation

Requires a readonly WaniKani API key and an OpenAI API token. Add them to `.env`.

Install and run the code:

```bash
pip install -e .
python wkagent.py
```

Connect to the local Gradio URL provided.