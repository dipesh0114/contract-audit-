CREATE DATABASE IF NOT EXISTS contract_audit;
USE contract_audit;

CREATE TABLE IF NOT EXISTS audits (
  id INT AUTO_INCREMENT PRIMARY KEY,      -- unique id per audited contract
  filename VARCHAR(255) NOT NULL,         -- original file name
  vendor VARCHAR(255),                    -- vendor name extracted by Claude
  contract_value VARCHAR(100),            -- e.g. "INR 12,00,000"
  expiry_date VARCHAR(50),                -- contract end date as text
  risk_level ENUM('High','Medium','Low'), -- overall risk
  risk_score INT,                         -- 0 (safe) to 100 (very risky)
  missing_clauses JSON,                   -- list of missing clauses
  key_deadlines JSON,                     -- list of {event, date}
  summary TEXT,                           -- 2-3 line plain-English summary
  full_text LONGTEXT,                     -- whole contract text (used later by chat/RAG)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
