import pandas as pd

# 1. Load the Usagi export file 
df_usagi = pd.read_csv("usagi_output.csv")

# 2. Filter for rows that actually mapped to a standard concept
df_filtered = df_usagi[df_usagi["conceptId"].notna() & (df_usagi["conceptId"] != 0)].copy()

# 3. Construct the OMOP STCM columns
df_stcm = pd.DataFrame()

df_stcm["source_code"] = df_filtered["sourceCode"]
df_stcm["source_concept_id"] = 0  # Default for custom local codes
df_stcm["source_vocabulary_id"] = "mimic_iv"  
df_stcm["source_code_description"] = df_filtered["sourceName"]
df_stcm["target_concept_id"] = df_filtered["conceptId"].astype(int)

df_stcm["target_vocabulary_id"] = df_filtered["domainId"]  

df_stcm["valid_start_date"] = "1970-01-01"
df_stcm["valid_end_date"] = "2099-12-31"
df_stcm["invalid_reason"] = None

# 4. Save to a new CSV ready for OMOP upload
df_stcm.to_csv("stcm_bilal.csv", index=False)
print("STCM file generated successfully!")