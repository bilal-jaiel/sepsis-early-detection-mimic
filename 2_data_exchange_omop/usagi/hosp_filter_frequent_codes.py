import pandas as pd
from pathlib import Path

# Récupère le dossier où se trouve le script
current_dir = Path(__file__).parent
file_path = current_dir / 'consolidated_usagi_master.csv'

# Lecture du fichier
df = pd.read_csv(file_path)

# CORRECTION : Filtrer les lignes où la colonne 'frequency' est supérieure à 10
filtered_df = df[df['frequency'] > 100]

# Enregistrer le DataFrame filtré
filtered_df.to_csv(current_dir / 'consolidated_usagi_sup100.csv', index=False)

print(f"Fini ! Nombre de lignes restantes : {len(filtered_df)}")