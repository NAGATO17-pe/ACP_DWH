"""
ETL/silver/facts/_base_processor.py
===================================
Base processor para componentes Silver (Facts).

Implementa des-duplicacion nativa en SQL Server via #Temp Tables
usando CREATE TABLE + executemany, que es el unico metodo confiable
para tablas temporales de sesion en pyodbc/SQLAlchemy.

-- POR QUE NO usamos pandas.to_sql() para #Temp Tables --
pandas.to_sql() crea la tabla en una conexion interna nueva que
SQL Server no puede ver desde la conexion activa del pipeline.
El warning "not found exactly as such" confirma este problema.
La solucion correcta es CREATE TABLE #Temp + executemany en la
misma conexion de la transaccion activa.

-- METODOS DE VALIDACION CON CACHE --
_validar_y_resolver_fecha, _validar_y_resolver_geografia,
_validar_y_resolver_variedad, _validar_y_resolver_personal
encapsulan la logica de lookup + cache que estaba duplicada en
cada fact. Las clases hijas los llaman directamente en _construir_payload.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError
from mdm.lookup import (
    obtener_parametros_pipeline,
    obtener_reglas_validacion,
    obtener_id_tiempo,
    obtener_id_geografia,
    obtener_id_variedad,
    obtener_id_personal,
    obtener_id_campana
)
from utils.tipos import a_entero, a_decimal, obtener_valor_raw as _get_raw
from silver.facts._helpers_fact_comunes import leer_bronce_dinamico, parsear_valores_raw

_log = logging.getLogger("ETL_Pipeline")


class BaseFactProcessor:
    # Niveles de calidad del circuit breaker (porcentaje de rechazo real sobre leídos)
    LIMITE_WARNING  = 1.0   # Emite WARNING en log, continúa
    LIMITE_ERROR    = 2.0   # Aborta el fact, bloquea Gold
    LIMITE_CRITICO  = 5.0   # Aborta el pipeline completo

    def __init__(self, engine: Engine, tabla_origen: str, tabla_destino: str, columna_id: str = None):
        self.engine = engine
        self.tabla_origen = tabla_origen
        self.tabla_destino = tabla_destino
        
        # Cargar configuración real de la base de datos
        self.config_params = obtener_parametros_pipeline(engine)
        self.reglas_dq = obtener_reglas_validacion(engine)
        
        # Prioridad: 1. Parametro explicito, 2. Guess por nombre de tabla
        self.columna_id = columna_id or f"ID_{self.tabla_origen.split('.')[-1]}"
        
        self.columnas_clave_unica: list[str] = []
        self.ids_procesados: list[int] = []
        self.ids_rechazados: list[int] = []
        
        self.resumen = {
            'leidos': 0,
            'insertados': 0,
            'rechazados': 0,
            'cuarentena': [],
            'rechazados_ids': [], # Nueva estructura para reporte de calidad refinado
            'resueltos_por_tiebreaker': 0,  # Duplicados intra-batch resueltos por timestamp
        }
        
        # Cache interna para lookups frecuentes
        self._cache_personal: dict[str, int | None] = {}
        self._cache_variedades: dict[str, int | None] = {}
        self._cache_geografia: dict[tuple, dict | None] = {}
        self._cache_tiempo: dict[Any, int | None] = {}

    def registrar_rechazo(
        self,
        id_origen: int,
        columna: str,
        valor: Any,
        motivo: str,
        tipo_regla: str = 'DQ',
        severidad: str = 'ALTO',
        fila: dict | None = None
    ) -> None:
        """
        Registra un rechazo en el resumen y lo prepara para la tabla MDM.Cuarentena.
        """
        # Si tenemos la fila, intentamos extraer el nombre del archivo para dar contexto
        contexto_archivo = ""
        if fila and fila.get('Nombre_Archivo'):
            contexto_archivo = f"[{fila.get('Nombre_Archivo')}] "

        self.resumen['rechazados'] = self.resumen.get('rechazados', 0) + 1
        self.resumen['rechazados_ids'].append({
            'id': id_origen,
            'es_duplicado_externo': False
        })
        if id_origen is not None:
            self.ids_rechazados.append(id_origen)
        self.resumen['cuarentena'].append({
            'columna': columna,
            'valor': str(valor) if valor is not None else 'NULL',
            'motivo': f"{contexto_archivo}{motivo}",
            'severidad': severidad,
            'tipo_regla': tipo_regla,
            'id_registro_origen': id_origen,
        })

    # ── utilidades de extraccion y conversion ──────────────────────────────────

    def parsear_raw(self, texto: str | None) -> dict[str, str]:
        """Envuelve parsear_valores_raw de helpers."""
        return parsear_valores_raw(texto)

    def get_raw_val(self, fila: Any, col: str, dict_raw: dict | None = None) -> Any:
        """
        Busca un valor de forma robusta:
        1. En la fila (DataFrame/Dict) con el nombre exacto.
        2. En el dict_raw (Valores_Raw) con el nombre exacto.
        3. En el dict_raw de forma insensible a mayúsculas/minúsculas.
        """
        # 1. Intento exacto en fila
        if hasattr(fila, 'get'):
            val = fila.get(col)
        elif hasattr(fila, col):
            val = getattr(fila, col)
        else:
            val = None
        
        if val is not None and str(val).strip() not in ('', 'None', 'nan'):
            return val

        if not dict_raw:
            return None

        # 2. Intento exacto en dict_raw
        val = dict_raw.get(col)
        if val is not None and str(val).strip() not in ('', 'None', 'nan'):
            return val
        
        # 3. Búsqueda insensible a mayúsculas/minúsculas en dict_raw
        col_lower = col.lower()
        for k, v in dict_raw.items():
            if k.lower() == col_lower:
                if v is not None and str(v).strip() not in ('', 'None', 'nan'):
                    return v
        
        return None

    def a_int(self, valor: Any) -> int | None:
        """Conversion segura a entero."""
        return a_entero(valor)

    def a_decimal(self, valor: Any) -> float | None:
        """Conversion segura a decimal."""
        return a_decimal(valor)

    def leer_bronce(self, columnas_raw: list[str], filtro_estado: bool = True) -> Any:
        """
        Lee la tabla origen usando el helper dinamico. 
        Evita duplicar la logica de SELECT y COLUMN_NAME en cada fact.
        """
        return leer_bronce_dinamico(
            self.engine, 
            self.tabla_origen, 
            self.columna_id, 
            columnas_raw, 
            filtro_estado=filtro_estado
        )

    # ── validaciones con cache (reutilizables por todas las clases hijas) ────────

    def _validar_y_resolver_fecha(
        self,
        id_origen: int,
        valor_fecha: Any,
        dominio: str,
    ) -> Any | None:
        """
        Llama procesar_fecha() + obtener_id_tiempo() con cache interno.
        Registra rechazo automaticamente si la fecha es invalida.
        Retorna el objeto fecha (date/datetime) o None si falla.
        """
        from utils.fechas import procesar_fecha, obtener_id_tiempo

        cache_key = (str(valor_fecha), dominio)
        if cache_key in self._cache_tiempo:
            resultado = self._cache_tiempo[cache_key]
            if resultado is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='Fecha_Raw',
                    valor=valor_fecha,
                    motivo='Fecha invalida o fuera de campana',
                )
            return resultado

        fecha, valida = procesar_fecha(valor_fecha, dominio=dominio)
        if not valida:
            self._cache_tiempo[cache_key] = None
            self.registrar_rechazo(
                id_origen,
                columna='Fecha_Raw',
                valor=valor_fecha,
                motivo='Fecha invalida o fuera de campana',
            )
            return None

        self._cache_tiempo[cache_key] = fecha
        return fecha

    def _validar_y_resolver_geografia(
        self,
        id_origen: int,
        fundo: Any,
        modulo_raw: Any,
        turno: Any = None,
        valvula: Any = None,
        cama: Any = None,
        sector: Any = None,
    ) -> dict | None:
        """
        Llama es_test_block() + normalizar_modulo() + resolver_geografia() con cache.
        Registra rechazo automaticamente si la geografia no se resuelve.
        Retorna el dict resultado_geo (con 'id_geografia') o None si falla.

        sector es opcional y mantenido como keyword-only para compatibilidad
        con facts que no lo traen (la mayoria). Solo Conteo_Fenologico lo usa.
        """
        from utils.texto import es_test_block, normalizar_modulo
        from mdm.lookup import resolver_geografia
        from silver.facts._helpers_fact_comunes import motivo_cuarentena_geografia

        modulo = normalizar_modulo(modulo_raw)
        cache_key = (str(fundo), str(sector), str(modulo), str(turno), str(valvula), str(cama))

        if cache_key in self._cache_geografia:
            resultado = self._cache_geografia[cache_key]
            if resultado is None or not resultado.get('id_geografia'):
                self.registrar_rechazo(
                    id_origen,
                    columna='Modulo_Raw',
                    valor=f"Fundo={fundo} | Sector={sector} | Modulo={modulo_raw} | Turno={turno} | Valvula={valvula}",
                    motivo=motivo_cuarentena_geografia(resultado or {}),
                    tipo_regla='MDM',
                )
                return None
            return resultado

        resultado = resolver_geografia(fundo, sector, modulo, self.engine, turno=turno, valvula=valvula, cama=cama)
        self._cache_geografia[cache_key] = resultado

        if not resultado or not resultado.get('id_geografia'):
            self.registrar_rechazo(
                id_origen,
                columna='Modulo_Raw',
                valor=f"Fundo={fundo} | Sector={sector} | Modulo={modulo_raw} | Turno={turno} | Valvula={valvula}",
                motivo=motivo_cuarentena_geografia(resultado or {}),
                tipo_regla='MDM',
            )
            return None

        return resultado

    def _validar_y_resolver_variedad(
        self,
        id_origen: int,
        variedad_canonica: Any,
        variedad_raw: Any = None,
    ) -> int | None:
        """
        Llama obtener_id_variedad() con cache interno.
        Registra rechazo automaticamente si no hay match en Dim_Variedad.
        Retorna ID_Variedad (int) o None si falla.
        """
        from mdm.lookup import obtener_id_variedad

        cache_key = str(variedad_canonica)
        if cache_key in self._cache_variedades:
            id_var = self._cache_variedades[cache_key]
            if id_var is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='Variedad_Raw',
                    valor=variedad_raw if variedad_raw is not None else variedad_canonica,
                    motivo='Variedad sin match en Dim_Variedad',
                    tipo_regla='MDM',
                )
            return id_var

        id_var = obtener_id_variedad(variedad_canonica, self.engine)
        self._cache_variedades[cache_key] = id_var

        if not id_var:
            self.registrar_rechazo(
                id_origen,
                columna='Variedad_Raw',
                valor=variedad_raw if variedad_raw is not None else variedad_canonica,
                motivo='Variedad sin match en Dim_Variedad',
                tipo_regla='MDM',
            )
            return None

        return id_var

    def _validar_y_resolver_personal(
        self,
        valor_dni: Any,
    ) -> int | None:
        """
        Llama procesar_dni() + obtener_id_personal() con cache interno.
        NO registra rechazo: personal ausente es aceptable (retorna None/-1).
        Retorna ID_Personal (int) o None si el DNI no es resolvible.
        """
        from utils.dni import procesar_dni
        from mdm.lookup import obtener_id_personal

        cache_key = str(valor_dni)
        if cache_key in self._cache_personal:
            return self._cache_personal[cache_key]

        dni, _ = procesar_dni(valor_dni)
        id_personal = obtener_id_personal(dni, self.engine)
        self._cache_personal[cache_key] = id_personal
        return id_personal

    # ── helpers internos ───────────────────────────────────────────────────────

    def _tipo_sql_para_valor(self, valor: Any) -> str:
        """Infiere el tipo SQL Server para un valor no-nulo."""
        import datetime
        if isinstance(valor, bool):
            return "BIT"
        if isinstance(valor, int):
            return "BIGINT"
        if isinstance(valor, float):
            return "FLOAT"
        if isinstance(valor, (datetime.date, datetime.datetime)):
            return "DATETIME2"
        return "NVARCHAR(4000)"

    def _inferir_tipo_columna(self, lista_dicts: list[dict], col: str) -> str:
        """
        Devuelve el tipo SQL para 'col' buscando el primer valor no-nulo en el batch.
        Evita el bug de inferir NVARCHAR(MAX) cuando la primera fila tiene None en
        una columna numérica, lo que causaría implicit conversions en el JOIN contra
        la fact e invalidaría los índices de la #Temp table.
        """
        for row in lista_dicts:
            val = row.get(col)
            if val is not None:
                return self._tipo_sql_para_valor(val)
        return "NVARCHAR(4000)"

    def _crear_y_cargar_temp(
        self,
        conexion,
        nombre_temp: str,
        cols_con_tipos: list[tuple[str, str]],
        lista_dicts: list[dict],
        columnas: list[str],
    ) -> None:
        """
        Delega en utils.sql_lotes.crear_e_insertar_temp: crea la #Temp table y
        la carga en la misma sesión/transacción activa del pipeline.

        Centraliza el patrón DROP/CREATE/INSERT que antes estaba duplicado entre
        _crear_tabla_temp_en_sesion + _insertar_en_temp aquí y en sql_lotes.
        """
        from utils.sql_lotes import crear_e_insertar_temp
        datos = [tuple(row.get(c) for c in columnas) for row in lista_dicts]
        crear_e_insertar_temp(conexion, nombre_temp, cols_con_tipos, datos)

    def _limpiar_duplicados_internos(self, lista_dicts: list[dict]) -> list[dict]:
        """
        Detecta duplicados dentro del mismo batch (Excel).

        Si self.columna_tiebreaker_timestamp está definida, aplica la política
        "último timestamp gana": entre filas con la misma clave se conserva la
        de mayor timestamp; los descartados NO van a Cuarentena (son re-mediciones
        legítimas, no errores de datos).

        Sin tiebreaker (comportamiento original): se conserva el primero visto y
        el duplicado se registra como DUPLICADO_INTERNO severidad MEDIO.
        """
        if not self.columnas_clave_unica:
            return lista_dicts

        tiebreaker = getattr(self, 'columna_tiebreaker_timestamp', None)

        if tiebreaker:
            # Agrupar por clave; quedarse con el de mayor timestamp
            EPOCH = __import__('datetime').datetime(1900, 1, 1)
            mejor: dict[tuple, dict] = {}
            resueltos_por_tiebreaker = 0
            for row in lista_dicts:
                clave = tuple(row.get(c) for c in self.columnas_clave_unica)
                ts = row.get(tiebreaker) or EPOCH
                if clave not in mejor:
                    mejor[clave] = row
                else:
                    ts_actual = mejor[clave].get(tiebreaker) or EPOCH
                    if ts > ts_actual:
                        mejor[clave] = row
                        resueltos_por_tiebreaker += 1
                    else:
                        resueltos_por_tiebreaker += 1
            if resueltos_por_tiebreaker:
                self.resumen['resueltos_por_tiebreaker'] = (
                    self.resumen.get('resueltos_por_tiebreaker', 0) + resueltos_por_tiebreaker
                )
                _log.info(
                    f"[{self.tabla_destino}] Dedup intra-batch por tiebreaker "
                    f"'{tiebreaker}': {resueltos_por_tiebreaker} descartado(s), "
                    f"queda la medición más reciente."
                )
            return list(mejor.values())

        # Comportamiento original sin tiebreaker
        vistos = set()
        lista_limpia = []

        for row in lista_dicts:
            clave = tuple(row.get(c) for c in self.columnas_clave_unica)

            if clave in vistos:
                id_origen = row.get("id_origen_rastreo")
                if id_origen is not None:
                    valor_resumen = " | ".join([str(v) for v in clave])
                    self.registrar_rechazo(
                        id_origen=id_origen,
                        columna=",".join(self.columnas_clave_unica),
                        valor=valor_resumen,
                        motivo=f"Registro duplicado dentro del mismo archivo para {self.tabla_destino}",
                        tipo_regla='DUPLICADO_INTERNO',
                        severidad='MEDIO',
                        fila=row
                    )
                    if id_origen in self.ids_procesados:
                        self.ids_procesados.remove(id_origen)
            else:
                vistos.add(clave)
                lista_limpia.append(row)

        return lista_limpia

    def pre_limpiar_duplicados_batch(self, df: pd.DataFrame, columnas_clave_negocio: list[str]) -> pd.DataFrame:
        """
        Deduplica un DataFrame de Bronce antes de procesarlo, para evitar trabajo en vano.
        Útil para Facts con mucho volumen y duplicados técnicos.
        """
        if df.empty or not columnas_clave_negocio:
            return df
            
        # Detectar la columna de ID (original o alias común)
        col_id_actual = self.columna_id
        if col_id_actual not in df.columns and 'ID_Registro_Origen' in df.columns:
            col_id_actual = 'ID_Registro_Origen'
        elif col_id_actual not in df.columns:
            # Si no hay ID, no podemos trackear el descarte, solo deduplicamos
            _log.warning(f"[{self.tabla_destino}] No se encontró columna ID ({self.columna_id}) para trackear descartes.")
            return df.drop_duplicates(subset=[c for c in columnas_clave_negocio if c in df.columns], keep='first')

        # Aseguramos que las columnas de negocio existen en el DF
        cols_finales = [c for c in columnas_clave_negocio if c in df.columns]
        if not cols_finales:
            return df

        # Capturar IDs de los que vamos a descartar (los que NO son el 'first')
        df_duplicados = df[df.duplicated(subset=cols_finales, keep='first')]
        if not df_duplicados.empty:
            ids_a_descartar = df_duplicados[col_id_actual].dropna().unique().tolist()
            self.ids_procesados.extend([int(i) for i in ids_a_descartar])
            _log.info(f"Deduplicación temprana: {len(ids_a_descartar)} IDs marcados para descarte (redundantes).")

        # Mantenemos el primero de cada grupo
        df_limpio = df.drop_duplicates(subset=cols_finales, keep='first')
        return df_limpio

    # ── metodo principal ───────────────────────────────────────────────────────

    def _ejecutar_insercion_masiva_segura(
        self,
        contexto: ContextoTransaccionalETL,
        lista_dicts: list[dict],
        nombre_temp: str,
    ) -> None:
        """
        Deduplicacion y carga masiva en 5 pasos sin consumir RAM del servidor.

        1. Deduplicación interna: limpia duplicados dentro del mismo batch.
        2. Inferir tipos SQL escaneando el batch completo por columna.
        3+4. Crear #Temp e insertar batch vía crear_e_insertar_temp (helper compartido).
        5. Detectar duplicados con INNER JOIN contra la tabla destino.
        6. Insertar solo los NO-duplicados con WHERE NOT EXISTS / MERGE tiebreaker.
        """
        if not lista_dicts:
            return

        # 0. Inyección automática de ID_Campana (Nueva Arquitectura)
        if any('ID_Campana' not in row for row in lista_dicts):
            from mdm.lookup import obtener_id_campana
            _cache_campana_local: dict[tuple, Any] = {}
            lista_original = lista_dicts
            lista_dicts = []
            
            for row in lista_original:
                if 'ID_Campana' not in row:
                    id_geo  = row.get('ID_Geografia')
                    id_var  = row.get('ID_Variedad')
                    id_mod  = row.get('_id_modulo_catalogo')
                    fecha   = row.get('Fecha_Evento') or row.get('Fecha') or row.get('Fecha_Cosecha')
                    fecha_k = str(fecha)[:10] if fecha is not None else None
                    clave   = (id_geo, id_var, id_mod, fecha_k)
                    
                    if clave not in _cache_campana_local:
                        _cache_campana_local[clave] = obtener_id_campana(id_geo, id_var, fecha, self.engine, id_modulo_catalogo=id_mod)
                    
                    id_campana = _cache_campana_local[clave]
                    row['ID_Campana'] = id_campana
                
                lista_dicts.append(row)

        # 1. Deduplicación interna en memoria (para evitar IntegrityError en el INSERT final)
        lista_dicts_limpia = self._limpiar_duplicados_internos(lista_dicts)
        
        if not lista_dicts_limpia:
             return

        conexion = contexto._conexion_activa()
        todas_cols = list(lista_dicts_limpia[0].keys())

        # 2. Inferir tipos SQL escaneando el batch completo por columna
        cols_con_tipos: list[tuple[str, str]] = [
            (col, self._inferir_tipo_columna(lista_dicts_limpia, col))
            for col in todas_cols
        ]

        # 3+4. Crear #Temp e insertar batch en un solo paso (helper compartido)
        self._crear_y_cargar_temp(conexion, nombre_temp, cols_con_tipos, lista_dicts_limpia, todas_cols)

        # 5. Detectar duplicados (Filtrando columnas que existen en el destino para evitar error 42S22)
        columnas_fisicas_key = [c for c in self.columnas_clave_unica if c in todas_cols and c != 'id_origen_rastreo']
        if not columnas_fisicas_key:
            raise ValueError(
                f"[{self.tabla_destino}] columnas_clave_unica no tiene interseccion con el payload. "
                f"Clave definida: {self.columnas_clave_unica} | Columnas en payload: {todas_cols}"
            )
        clausula_on_tmp = " AND ".join([f"tmp.[{c}] = dest.[{c}]" for c in columnas_fisicas_key])
        clausula_on_src = " AND ".join([f"src.[{c}] = dest.[{c}]" for c in columnas_fisicas_key])

        # Columnas físicas para INSERT/UPDATE (excluir auxiliares internas y de rastreo)
        columnas_dest = [c for c in todas_cols if c != 'id_origen_rastreo' and not c.endswith('_Virtual') and not c.startswith('_')]

        tiebreaker = getattr(self, 'columna_tiebreaker_timestamp', None)

        if tiebreaker and tiebreaker in todas_cols:
            # 6-TB. MERGE "último timestamp gana"
            # Las filas nuevas se insertan; las existentes se actualizan solo si el
            # timestamp entrante es estrictamente mayor al ya almacenado.
            col_update = ", ".join(
                [f"dest.[{c}] = src.[{c}]" for c in columnas_dest if c not in columnas_fisicas_key]
            )
            col_insert_list = ", ".join([f"[{c}]" for c in columnas_dest])
            col_values_list = ", ".join([f"src.[{c}]" for c in columnas_dest])

            # El tiebreaker es una columna interna del batch (ej. _fecha_registro_dt)
            # que puede no existir en la tabla destino. Comparamos contra Fecha_Sistema
            # del destino como fallback seguro para decidir cuál registro es más reciente.
            sql_merge = text(f"""
                MERGE {self.tabla_destino} AS dest
                USING {nombre_temp} AS src
                ON ({clausula_on_src})
                WHEN MATCHED AND ISNULL(src.[{tiebreaker}], '19000101') > ISNULL(dest.[Fecha_Sistema], '19000101')
                    THEN UPDATE SET {col_update}
                WHEN NOT MATCHED BY TARGET
                    THEN INSERT ({col_insert_list}) VALUES ({col_values_list})
                OUTPUT $action;
            """)
            filas_accion = conexion.execute(sql_merge).fetchall()
            n_insert = sum(1 for r in filas_accion if r[0] == 'INSERT')
            n_update = sum(1 for r in filas_accion if r[0] == 'UPDATE')
            self.resumen['insertados'] += n_insert
            self.resumen.setdefault('actualizados_por_tiebreaker', 0)
            self.resumen['actualizados_por_tiebreaker'] += n_update
            if n_update:
                _log.info(
                    f"[{self.tabla_destino}] MERGE tiebreaker: {n_insert} INSERT, "
                    f"{n_update} UPDATE (timestamp más reciente ganó)."
                )
        else:
            # 5-orig. Detectar duplicados externos y marcarlos
            sql_duplicados = text(f"""
                SELECT tmp.[id_origen_rastreo]
                FROM {nombre_temp} tmp
                INNER JOIN {self.tabla_destino} dest ON {clausula_on_tmp}
            """)
            duplicados = conexion.execute(sql_duplicados).fetchall()
            ids_duplicados = {int(d[0]) for d in duplicados if d[0] is not None}

            for id_dup in ids_duplicados:
                if 'rechazados_ids' not in self.resumen:
                    self.resumen['rechazados_ids'] = []
                self.resumen['rechazados_ids'].append({
                    'id': id_dup,
                    'es_duplicado_externo': True
                })
                if id_dup in self.ids_procesados:
                    self.ids_procesados.remove(id_dup)
                self.ids_rechazados.append(id_dup)

            # 6-orig. INSERT solo los nuevos via WHERE NOT EXISTS
            col_select = ", ".join([f"tmp.[{c}]" for c in columnas_dest])
            col_insert = ", ".join([f"[{c}]" for c in columnas_dest])

            sql_insert = text(f"""
                INSERT INTO {self.tabla_destino} ({col_insert})
                SELECT {col_select}
                FROM {nombre_temp} tmp
                WHERE NOT EXISTS (
                    SELECT 1 FROM {self.tabla_destino} dest
                    WHERE {clausula_on_tmp}
                )
            """)
            resultado = conexion.execute(sql_insert)
            self.resumen['insertados'] += resultado.rowcount

        # 7. Limpieza
        conexion.execute(text(f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"))

    # ── finalizacion ───────────────────────────────────────────────────────────

    def finalizar_proceso(self, contexto: ContextoTransaccionalETL) -> dict:
        """Marca estados de carga, reporta cuarentena y evalua el Circuit Breaker."""
        
        if self.ids_procesados:
            contexto.marcar_estado_carga(self.tabla_origen, self.columna_id, self.ids_procesados)
        if self.ids_rechazados:
            contexto.marcar_estado_carga(self.tabla_origen, self.columna_id, self.ids_rechazados, estado='RECHAZADO')
        if self.resumen.get('cuarentena'):
            contexto.enviar_cuarentena(self.tabla_origen, self.resumen['cuarentena'])

        # ── Resumen de Continuidad ─────────────────────────────────────────────
        
        # 3. Calcular rechazo real (ignoring already existing technical duplicates)
        # Solo contamos como rechazo de CALIDAD lo que no es un duplicado externo
        lista_rechazos = self.resumen.get('rechazados_ids', [])
        rechazos_reales = [r for r in lista_rechazos if not r.get('es_duplicado_externo', False)]
        unique_ids_rechazados = len(set(r['id'] for r in rechazos_reales))
        
        total_leidos = self.resumen.get('leidos', 0)
        porcentaje_rechazo = (unique_ids_rechazados / total_leidos * 100) if total_leidos > 0 else 0
        
        # 4. Reporte final
        _log.info(f"-> {total_leidos} leidos | {self.resumen.get('insertados', 0)} insertados | {unique_ids_rechazados} rechazados reales | {int(porcentaje_rechazo)}% rechazo real")

        # ── Circuit Breaker de calidad ─────────────────────────────────────────
        # Muestra minima: con < 50 filas leidas, 1 rechazo ya dispara umbrales
        # estadisticamente irrelevantes (ej. 1/18 = 5.6% > 5% CRITICO). Ignorar.
        MIN_MUESTRA_BREAKER = 50
        nivel_bloqueo = None
        if total_leidos >= MIN_MUESTRA_BREAKER:
            if porcentaje_rechazo >= self.LIMITE_CRITICO:
                nivel_bloqueo = "CRITICO"
                _log.error(
                    f"[CIRCUIT BREAKER CRITICO] {self.tabla_destino}: "
                    f"{porcentaje_rechazo:.1f}% rechazo >= {self.LIMITE_CRITICO}% — "
                    f"ABORTANDO PIPELINE COMPLETO"
                )
                raise ErrorCircuitBreakerCritico(
                    f"Circuit breaker CRITICO en {self.tabla_destino}: "
                    f"{porcentaje_rechazo:.1f}% de rechazo ({unique_ids_rechazados}/{total_leidos}). "
                    f"Umbral crítico: {self.LIMITE_CRITICO}%."
                )
            elif porcentaje_rechazo >= self.LIMITE_ERROR:
                nivel_bloqueo = "ERROR"
                _log.error(
                    f"[CIRCUIT BREAKER ERROR] {self.tabla_destino}: "
                    f"{porcentaje_rechazo:.1f}% rechazo >= {self.LIMITE_ERROR}% — "
                    f"ABORTANDO FACT, GOLD BLOQUEADO"
                )
                raise ErrorCircuitBreakerError(
                    f"Circuit breaker ERROR en {self.tabla_destino}: "
                    f"{porcentaje_rechazo:.1f}% de rechazo ({unique_ids_rechazados}/{total_leidos}). "
                    f"Umbral de error: {self.LIMITE_ERROR}%."
                )
            elif porcentaje_rechazo >= self.LIMITE_WARNING:
                nivel_bloqueo = "WARNING"
                _log.warning(
                    f"[CIRCUIT BREAKER WARNING] {self.tabla_destino}: "
                    f"{porcentaje_rechazo:.1f}% rechazo >= {self.LIMITE_WARNING}% — "
                    f"continúa, pero revisar calidad."
                )

        return {
            'Tabla_Destino': self.tabla_destino,
            'Filas_Leidas_Bronce': total_leidos,
            'Filas_Insertadas': self.resumen.get('insertados', 0),
            'Nuevos_Casos_Cuarentena': unique_ids_rechazados,
            'cuarentena': self.resumen.get('cuarentena', []),
            'Bloqueo_Integridad': nivel_bloqueo == "WARNING",
            'Dependencias_Incumplidas': [],
            'resueltos_por_tiebreaker': self.resumen.get('resueltos_por_tiebreaker', 0),
        }
