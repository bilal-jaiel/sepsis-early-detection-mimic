import duckdb

con = duckdb.connect('mimic_iv.db')

# Get a list of all tables starting with 'v_'
tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'treated_%'").fetchall()

for table in tables:
    t_name = table[0]
    print(f"\n--- Variance Report: {t_name} ---")
    
    # Calculate variance for all numeric columns in the table
    # We use square of std from summarize for efficiency
    df = con.execute(f"""
        SELECT 
            column_name, 
            (CAST(std AS FLOAT)**2) as variance 
        FROM (SUMMARIZE {t_name}) 
        WHERE std IS NOT NULL
    """).df()
    
    print(df)