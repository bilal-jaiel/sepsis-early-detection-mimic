import duckdb
import os

base_path = os.path.dirname(os.path.abspath(__file__))
sql_path = os.path.join(base_path, "data_prep.sql")

con = duckdb.connect('mimic_iv.db')

with open('data_prep.sql', 'r') as f:
    con.execute(f.read())

print("Database initialized and saved to mimic_iv.db")