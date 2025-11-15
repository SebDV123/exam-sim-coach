# Exam Simulation Coach

This repository contains a minimal implementation of a web‑based exam simulator.
It is built with **FastAPI** for the backend and a simple **HTML/JavaScript**
front‑end.  The aim is to provide a foundation that you can deploy as
a website or progressive web application with minimal effort.  The
current implementation generates a fixed set of three questions and
includes an automatic marker that awards marks for correct multiple–choice
answers, keyword recognition in short answers and method/final answer
checks in calculation questions.

## Running locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Launch the server in development mode:

   ```bash
   uvicorn server:app --reload
   ```

3. Visit `http://127.0.0.1:8000/` in your browser.  You can adjust
   the board, level and subject fields for your own purposes – they
   are ignored by the dummy exam generator.

## Building and running with Docker

To containerise the application:

```bash
docker build -t exam-sim-coach .
docker run -p 8000:8000 exam-sim-coach
```

Then open `http://localhost:8000/`.

## Extending the implementation

The current dummy generator in `server.py` always returns the same
three questions.  To plug in a real question generator:

1. Modify the `generate_dummy_exam()` function to produce questions
   based on the input parameters (`board`, `level`, `subject`, `topics`).
2. Ensure each question dict follows the schema used in the `Question`
   model (type, stem, marks, etc.).

Similarly, the `mark_paper()` function can be adapted to reflect more
sophisticated marking schemes.  At present it awards partial credit
for matching keywords in short answers and assigns marks for calculation
questions based on recognised method keywords and the final answer.

You can also extend the front‑end in `static/index.html` to allow
users to pick topics, save their progress or download PDF copies of
their papers and mark schemes.