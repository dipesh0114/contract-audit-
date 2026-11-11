import os, json
import mysql.connector                      # MySQL driver
from dotenv import load_dotenv              # reads the .env file

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))   # always read backend/.env, whatever folder you run from

def get_conn():
    # Open a fresh connection per request (simple and safe for a demo app)
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),   # 3307 when MySQL runs in Docker
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "contract_audit"),
    )

def save_audit(filename, r, full_text):
    # r is the dict Claude returned. %s placeholders prevent SQL injection.
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """INSERT INTO audits (filename, vendor, contract_value, expiry_date,
           risk_level, risk_score, missing_clauses, key_deadlines, summary, full_text)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (filename, r.get("vendor"), r.get("contract_value"), r.get("expiry_date"),
         r.get("risk_level"), r.get("risk_score"),
         json.dumps(r.get("missing_clauses", [])),   # lists stored as JSON columns
         json.dumps(r.get("key_deadlines", [])),
         r.get("summary"), full_text))
    conn.commit()
    new_id = cur.lastrowid                  # id of the row we just inserted
    cur.close(); conn.close()
    return new_id

def list_audits(risk=None):
    # Dashboard data: everything except the big full_text column.
    # risk = "High" / "Medium" / "Low" filters the rows; None returns all.
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    sql = """SELECT id, filename, vendor, contract_value, expiry_date,
             risk_level, risk_score, missing_clauses, key_deadlines, summary, created_at
             FROM audits"""
    params = ()
    if risk in ("High", "Medium", "Low"):   # whitelist check, then parameterized query
        sql += " WHERE risk_level = %s"
        params = (risk,)
    cur.execute(sql + " ORDER BY id DESC", params)
    rows = cur.fetchall(); cur.close(); conn.close()
    for row in rows:                        # JSON columns come back as strings -> parse
        for k in ("missing_clauses", "key_deadlines"):
            if isinstance(row[k], str): row[k] = json.loads(row[k])
        row["created_at"] = str(row["created_at"])
    return rows

def get_text(audit_id):
    # Fetch the stored contract text so the chatbot can search inside it
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT full_text FROM audits WHERE id=%s", (audit_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row[0] if row else None

def get_all_texts(limit=50):
    # Full text of the most recent contracts, so the assistant can search ACROSS all of them
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, filename, vendor, full_text FROM audits ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def overview():
    # "What data do I have?" - computed with plain SQL/Python, no AI call, so it loads instantly
    rows = list_audits()
    by_risk = {"High": 0, "Medium": 0, "Low": 0}
    missing = {}
    for r in rows:
        if r["risk_level"] in by_risk: by_risk[r["risk_level"]] += 1
        for c in r["missing_clauses"]: missing[c] = missing.get(c, 0) + 1
    top_missing = [{"clause": c, "count": n} for c, n in sorted(missing.items(), key=lambda x: -x[1])[:5]]
    vendors = sorted({r["vendor"] for r in rows if r["vendor"] and r["vendor"] != "Not specified"})
    if not rows:                                        # nothing uploaded yet
        suggestions = ["What can this tool do?", "What kind of contracts can I upload?", "What does High risk mean?"]
    else:
        suggestions = ["Give me an overview of all my contracts"]
        if by_risk["High"]: suggestions.append("Show the High-risk contracts and explain why")
        suggestions += ["Which clauses are missing most often?", "What deadlines are coming up?",
                        "Explain contract #%d in simple words" % rows[0]["id"]]
    return {"total": len(rows), "by_risk": by_risk, "vendors": vendors, "top_missing": top_missing,
            "latest": rows[0]["filename"] if rows else None, "suggestions": suggestions[:4]}