import sys
import ollama

def main():
    print("Connecting to Ollama at http://127.0.0.1:11434...")
    client = ollama.Client(host="http://127.0.0.1:11434")
    model_name = "qwen2.5:1.5b"
    print(f"Starting pull for {model_name}...")

    last_status = None
    for res in client.pull(model_name, stream=True):
        status = res.get("status", "")
        completed = res.get("completed") or 0
        total = res.get("total") or 0
        if total > 0:
            pct = (completed / total) * 100
            msg = f"{status}: {pct:.1f}% ({completed // (1024*1024)}MB / {total // (1024*1024)}MB)"
            sys.stdout.write(f"\r{msg:70}")
            sys.stdout.flush()
        else:
            if status != last_status:
                print(f"\n{status}")
                last_status = status

    print(f"\nSuccessfully pulled {model_name}!")

    print("\nVerifying model in Ollama model list:")
    models = client.list()
    print(models)

if __name__ == "__main__":
    main()

