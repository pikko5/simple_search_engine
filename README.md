Simple Search Engine.

## How to Use


First, run:

```
pip install -r requirements.txt
```

To run the code, simply run:

```
uvicorn main:app --reload
```

To run via CLI:

```
python main_cli.py --feeds feeds.txt --query 'llm' --top_k 5
```