CREATE TABLE Businesses (
    business_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE Subscriptions (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    FOREIGN KEY (business_id) REFERENCES Businesses(business_id)
);

CREATE TABLE Employees (
    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL UNIQUE,
    business_id INTEGER NOT NULL,
    email TEXT NOT NULL,
    registration_code TEXT, -- Temporary code for linking
    FOREIGN KEY (business_id) REFERENCES Businesses(business_id)
);

CREATE TABLE ProjectAccess (
    access_id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    doc_id TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES Businesses(business_id)
);

CREATE TABLE QueryLogs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    resolution_status TEXT NOT NULL, -- 'resolved' or 'unresolved'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL,
    summary TEXT, -- Brief LLM-generated summary
    FOREIGN KEY (chat_id) REFERENCES Employees(chat_id)
);