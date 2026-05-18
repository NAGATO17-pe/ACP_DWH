import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import ejecutar_query

tables = ['Fact_Conteo_Fenologico','Fact_Peladas','Fact_Evaluacion_Pesos','Fact_Cosecha_SAP','Fact_Proyecciones']
for t in tables:
    r = ejecutar_query(
        f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA='Silver' AND TABLE_NAME='{t}' "
        f"AND COLUMNPROPERTY(OBJECT_ID('Silver.{t}'), COLUMN_NAME, 'IsIdentity')=1"
    )
    identity_cols = r['COLUMN_NAME'].tolist() if not r.empty else []
    print(f"{t}: identity_cols={identity_cols}")
