# 🧠 AnalizerDB – SQL Query Performance Analyzer for MySQL

This is a developer-friendly tool built with **Python + Streamlit** that connects to your **local MySQL server** (e.g., via **XAMPP**) and analyzes performance of SQL queries. The tool gives insight into:

- Query execution times
- Execution plan (EXPLAIN)
- Real execution data (ANALYZE)
- `performance_schema` metrics like I/O, index usage, threads, and active statements
- Automatic optimization tips and warnings

---

## ⚙️ Requirements

Before you start, make sure you have the following:

### ✅ Installed:

- [Python 3.9+](https://www.python.org/)
- [XAMPP (MySQL + phpMyAdmin)](https://www.apachefriends.org/index.html)
- [Git](https://git-scm.com/)

### ✅ Python packages:

Install with:

//bash
pip install streamlit mysql-connector-python pandas matplotlib

🚀 How to Run the App
1. Launch your MySQL server
Start XAMPP and enable MySQL.

2. Access phpMyAdmin
Go to:

arduino
Copy
Edit
http://localhost/phpmyadmin/
Create your test database(s) here if needed.

3. Clone the repository
bash
Copy
Edit
git clone https://github.com/PiotrGagorowski/AnalizerDB.git
cd AnalizerDB
4. Run the Streamlit app
bash
Copy
Edit
streamlit run app.py
This will open a browser window with the application.
