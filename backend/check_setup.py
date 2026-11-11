"""Run from the backend folder:  python check_setup.py
Tells you exactly what is wrong with your setup."""
import os, glob
from dotenv import load_dotenv

here = os.path.dirname(os.path.abspath(__file__))
print("Folder:", here)

# 1. .env file
env_files = [os.path.basename(f) for f in glob.glob(os.path.join(here, ".env*"))]
print("\n[1] Files starting with .env here:", env_files or "NONE")
env_path = os.path.join(here, ".env")
if not os.path.exists(env_path):
    print("   PROBLEM: no file named exactly '.env'. Rename .env.txt / .env.example to .env")
else:
    print("   OK: .env found")
load_dotenv(env_path)

# 2. values (secrets are hidden)
print("\n[2] Values read from .env")
for k in ("DB_HOST", "DB_PORT", "DB_USER", "DB_NAME", "CLAUDE_MODEL"):
    print(f"   {k} = {os.getenv(k)}")
print("   DB_PASSWORD set:", bool(os.getenv("DB_PASSWORD")))
print("   LLM_PROVIDER =", os.getenv("LLM_PROVIDER", "gemini"))
print("   GEMINI_API_KEY set:", bool(os.getenv("GEMINI_API_KEY")), "| ANTHROPIC_API_KEY set:", bool(os.getenv("ANTHROPIC_API_KEY")))

# 3. is ai.py the fixed version?
src = open(os.path.join(here, "ai.py"), encoding="utf-8").read()
print("\n[3] ai.py still contains 'temperature':", "temperature" in src)
if "temperature" in src:
    print("   PROBLEM: you are running the OLD ai.py. Replace it with the new one from the zip.")

# 4. MySQL
print("\n[4] MySQL connection")
try:
    import mysql.connector
    c = mysql.connector.connect(host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")), user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""), database=os.getenv("DB_NAME", "contract_audit"))
    cur = c.cursor(); cur.execute("SHOW TABLES"); print("   OK. Tables:", [t[0] for t in cur.fetchall()]); c.close()
except Exception as e:
    print("   PROBLEM:", e)

# 5. AI provider
print("\n[5] AI provider")
try:
    import ai
    print("   provider:", ai.PROVIDER)
    print("   reply:", ai.llm("Reply with the single word OK", max_tokens=20))
except Exception as e:
    print("   PROBLEM:", e)
    if os.getenv("LLM_PROVIDER", "gemini") == "gemini":
        # Show which models your key can actually use, so you can pick one for GEMINI_MODEL
        try:
            import requests
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=100",
                             headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", "")}, timeout=30)
            names = [m["name"].replace("models/", "") for m in r.json().get("models", [])
                     if "generateContent" in m.get("supportedGenerationMethods", [])]
            print("   Models your key can use:", ", ".join(n for n in names if "gemini" in n))
        except Exception as e2:
            print("   (could not list models:", e2, ")")