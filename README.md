pip install -r requirements.txt

uvicorn backend.main:app --reload python worker/worker.py
