import sys
sys.path.append(r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")
from config.conexion import obtener_engine
from sqlalchemy import text
from pathlib import Path

def generate_dbml_via_sql(engine):
    dbml_lines = []
    schemas_of_interest = "('Bronce', 'Silver', 'Gold', 'Control', 'dbo')"
    
    with engine.connect() as conn:
        # Get tables
        tables_query = f"""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND TABLE_SCHEMA IN {schemas_of_interest}
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        tables = conn.execute(text(tables_query)).fetchall()
        
        # Get columns
        columns_query = f"""
            SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA IN {schemas_of_interest}
            ORDER BY ORDINAL_POSITION
        """
        columns = conn.execute(text(columns_query)).fetchall()
        
        # Map columns to tables
        table_cols = {}
        for c in columns:
            t_key = f"{c[0]}.{c[1]}"
            if t_key not in table_cols:
                table_cols[t_key] = []
            
            ctype = c[3]
            if c[5] is not None and c[5] > 0:
                ctype += f"({c[5]})"
            elif c[5] == -1:
                ctype += "(max)"
            
            table_cols[t_key].append({
                'name': c[2],
                'type': ctype,
                'nullable': c[4] == 'YES'
            })
            
        # Primary Keys
        pk_query = f"""
            SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
              ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
              AND tc.TABLE_SCHEMA IN {schemas_of_interest}
        """
        pks = conn.execute(text(pk_query)).fetchall()
        pk_set = set(f"{r[0]}.{r[1]}.{r[2]}" for r in pks)
        
        # Foreign Keys
        fk_query = f"""
            SELECT 
                SCHEMA_NAME(fk.schema_id) AS TABLE_SCHEMA,
                OBJECT_NAME(fk.parent_object_id) AS TABLE_NAME,
                c1.name AS COLUMN_NAME,
                SCHEMA_NAME(t.schema_id) AS REF_SCHEMA,
                OBJECT_NAME(fk.referenced_object_id) AS REF_TABLE,
                c2.name AS REF_COLUMN
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.columns c1 ON fkc.parent_object_id = c1.object_id AND fkc.parent_column_id = c1.column_id
            INNER JOIN sys.columns c2 ON fkc.referenced_object_id = c2.object_id AND fkc.referenced_column_id = c2.column_id
            INNER JOIN sys.tables t ON fk.referenced_object_id = t.object_id
            WHERE SCHEMA_NAME(fk.schema_id) IN ('Bronce', 'Silver', 'Gold', 'Control', 'dbo')
        """
        fks = conn.execute(text(fk_query)).fetchall()
        
        for t in tables:
            schema = t[0]
            tname = t[1]
            t_key = f"{schema}.{tname}"
            
            dbml_lines.append(f'Table "{schema}"."{tname}" {{')
            
            cols = table_cols.get(t_key, [])
            for c in cols:
                cname = c['name']
                settings = []
                if f"{t_key}.{cname}" in pk_set:
                    settings.append("pk")
                if not c['nullable']:
                    settings.append("not null")
                
                settings_str = f" [{', '.join(settings)}]" if settings else ""
                
                # Replace spaces in data types for DBML compatibility
                ctype = c['type'].replace(" ", "_")
                
                dbml_lines.append(f'  "{cname}" {ctype}{settings_str}')
                
            dbml_lines.append("}")
            dbml_lines.append("")
            
        # Print Foreign Keys
        for fk in fks:
            dbml_lines.append(f'Ref: "{fk[0]}"."{fk[1]}"."{fk[2]}" > "{fk[3]}"."{fk[4]}"."{fk[5]}"')
            
    return "\n".join(dbml_lines)

if __name__ == "__main__":
    engine = obtener_engine()
    dbml_content = generate_dbml_via_sql(engine)
    
    output_path = Path(r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\database.dbml")
    output_path.write_text(dbml_content, encoding="utf-8")
    print(f"DBML generated at {output_path}")
