import psycopg2

conn = psycopg2.connect(
    dbname="helpdesk",
    user="postgres",
    password="bot1234",
    host="localhost",
    port="5432"
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM queries;")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
