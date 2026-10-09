import pandas as pd
import numpy as np
import os
import re
import unicodedata

def to_snake_case(name):
    if not isinstance(name, str):
        return name
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    name = re.sub(r'[^a-zA-Z0-9]', ' ', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name.lower()

def limpiar_nombre_columna_nivel0(col):
    if not isinstance(col, str):
        if pd.isna(col) or isinstance(col, (int, float)):
            return ""
        return str(col)
    col = re.sub(r'^\d+\s*[-]?\s*', '', col)
    col = col.replace('\n', ' ').strip()
    while '  ' in col:
        col = col.replace('  ', ' ')
    return col

def limpiar_nombre_columna_nivel1(col):
    if not isinstance(col, str):
        if pd.isna(col):
            return ""
        return str(col)
    col = col.replace('\n', ' ').strip()
    while '  ' in col:
        col = col.replace('  ', ' ')
    return col

def classify_event_column(col_name):
    """
    Toma el nombre aplanado de la columna (Ej: 'PRUEBAS PADRON - FECHA') 
    y devuelve una tupla: (nombre_evento, id_vehiculo, intento, atributo_extraido)
    Retorna None si la columna no es de eventos.
    """
    col_upper = col_name.upper()
    
    # === 1. INGRESO ===
    # Omitimos INGRESO porque es un campo calculado (mínimo de certificados)
    if 'INGRESO - FECHA PRIMER C.I' in col_upper:
        return None
        
    # === 2. NOVEDAD y RESTRICCION MEDICA ===
    if 'NOVEDADES - NOVEDAD' in col_upper:
        return ('observacion', None, None, 'OBSERVACION')
    if 'NOVEDADES - RESTRICCI' in col_upper:
        return ('restriccion medica', None, None, 'RESTRICCION MEDICA')
    if 'NOVEDADES - ELEMENTO DE PROTECCI' in col_upper:
        return ('restriccion medica', None, None, 'ELEMENTO DE PROTECCION')
    if 'NOVEDADES - DESDE' in col_upper:
        return ('restriccion medica', None, None, 'INICIO RESTRICCION MEDICA')
    if 'NOVEDADES - HASTA' in col_upper:
        return ('restriccion medica', None, None, 'FIN RESTRICCION MEDICA')
        
    # Función auxiliar para extraer el número de intento
    def extract_intento(text):
        m = re.search(r'\b(\d+)\b', text)
        return int(m.group(1)) if m else None

    # === 3. CERTIFICADOS DE IDONEIDAD (Col 20-36) ===
    if 'CERTIFICADOS DE IDONEIDAD RECIBIDOS' in col_upper:
        parte_final = col_upper.split('-')[-1].strip()
        intento = extract_intento(parte_final)
        
        if 'COMPLEMENTARIO' in parte_final:
            return ('certificacion', 3, None, 'FECHA CERTIFICADO')
        if 'PADRON' in parte_final:
            return ('certificacion', 2, None, 'FECHA CERTIFICADO')
        if 'ARTICULADO' in parte_final:
            return ('certificacion', 1, None, 'FECHA CERTIFICADO')
            
        if 'RENOVACI' in parte_final:
            return ('renovacion', None, intento, 'FECHA CERTIFICADO')
        if 'REACTIVACI' in parte_final:
            return ('reactivacion', None, intento, 'FECHA CERTIFICADO')
            
        # Omitimos VENCIMIENTO y ULTIMA MODIFICACION porque son campos calculados (fórmulas) en el Excel
        if 'VENCIMIENTO' in parte_final or 'MODIFICACION' in parte_final:
            return None

    # === 4. PRUEBAS (Col 46-75) ===
    if 'PRUEBA' in col_upper:
        parte_inicio = col_upper.split('-')[0].strip()
        parte_final = col_upper.split('-')[-1].strip()
        
        intento = extract_intento(parte_inicio)
        
        attr = 'EVALUADOR' if 'EVALUADOR' in parte_final else 'FECHA PRUEBA'
        if 'CÓDIGO' in parte_final or 'CODIGO' in parte_final: return None
        if 'CURSO' in parte_final: return None
        if 'FLUJO' in parte_final: return None
        
        if 'COMPLEMENTARIO' in parte_inicio:
            return ('certificacion', 3, None, attr)
        if 'PADRON' in parte_inicio:
            return ('certificacion', 2, None, attr)
        if 'ARTICULADO' in parte_inicio:
            return ('certificacion', 1, None, attr)
            
        if 'RENOVACI' in parte_inicio:
            return ('renovacion', None, intento, attr)
        if 'REACTIVACI' in parte_inicio:
            return ('reactivacion', None, intento, attr)

    # === 5. MODIFICACIONES AL CERTIFICADO (Col 37-44) ===
    if 'MODIFICACIONES AL CERTIFICADO' in col_upper:
        parte_final = col_upper.split('-')[-1].strip()
        intento = extract_intento(parte_final)
        
        if 'SUSPENSI' in parte_final:
            return ('suspension', None, intento, 'FECHA SUSPENSION')
        if 'CANCELACI' in parte_final:
            return ('cancelacion', None, None, 'FECHA RETIRO')
        if 'NOTIFICACI' in parte_final:
            return ('cancelacion', None, None, 'FECHA NOTIFICACION RETIRO')

    return None

def main():
    archivo_entrada = r'C:\Users\maortiz\OneDrive - metrocali.gov.co\Scripts\Proyecto_BD_operadores\Archivos_excel_iniciales\BASE DE DATOS OPERADORESv4.xlsm'
    
    if not os.path.exists(archivo_entrada):
        print(f"Error: El archivo {archivo_entrada} no existe en el directorio actual.")
        return

    print("Leyendo el archivo Excel... (Esto tomará un momento)")
    df = pd.read_excel(archivo_entrada, sheet_name='BD', header=[1, 2], engine='openpyxl')
    
    # Aplanar y limpiar columnas
    nuevas_columnas = []
    last_level_0 = ""
    
    for col_level_0, col_level_1 in df.columns:
        c0 = limpiar_nombre_columna_nivel0(col_level_0)
        c1 = limpiar_nombre_columna_nivel1(col_level_1)
        
        if 'Unnamed' in c0 or c0 == "":
            c0 = last_level_0 if last_level_0 != "" else ""
        else:
            last_level_0 = c0
            
        if 'Unnamed' in c1:
            c1 = ""
            
        if c0 and c1:
            nuevo_nombre = f"{c0} - {c1}"
        elif c0:
            nuevo_nombre = c0
        elif c1:
            nuevo_nombre = c1
        else:
            nuevo_nombre = "COLUMNA_SIN_NOMBRE"
            
        nuevas_columnas.append(nuevo_nombre)
        
    df.columns = nuevas_columnas
    
    # Deduplicar columnas
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): 
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    
    df.dropna(how='all', inplace=True)
    
    # --- 1. Dim_Vigencia_Registro ---
    print("Creando Dim_Vigencia_Registro...")
    dim_vigencia = pd.DataFrame({
        'id_vigencia': [1, 2],
        'condicion_fila': ['vigente', 'anulado']
    })
    id_vigencia_default = 1
    
    col_codigo = [c for c in df.columns if 'CODIGO' in c.upper()][0] if [c for c in df.columns if 'CODIGO' in c.upper()] else None
    if not col_codigo:
        df['CODIGO_GENERADO'] = range(1, len(df) + 1)
        col_codigo = 'CODIGO_GENERADO'

    # --- 2. Dim_Empresa ---
    print("Creando Dim_Empresa...")
    col_empresa = [c for c in df.columns if 'EMPRESA' in c.upper()]
    if col_empresa:
        empresas_unicas = df[col_empresa[0]].dropna().unique()
        empresas_unicas_limpias = [str(e).strip().title() for e in empresas_unicas]
        dim_empresa = pd.DataFrame({'nombre_empresa': pd.Series(empresas_unicas_limpias).unique()})
        dim_empresa.insert(0, 'id_empresa', range(1, len(dim_empresa) + 1))
        dim_empresa['id_vigencia'] = id_vigencia_default
        
        empresa_map = dict(zip(empresas_unicas, [str(e).strip().title() for e in empresas_unicas]))
        df['empresa_temp'] = df[col_empresa[0]].map(empresa_map)
        df = df.merge(dim_empresa[['id_empresa', 'nombre_empresa']], left_on='empresa_temp', right_on='nombre_empresa', how='left')
    else:
        dim_empresa = pd.DataFrame(columns=['id_empresa', 'nombre_empresa', 'id_vigencia'])
        df['id_empresa'] = np.nan

    # --- 3. Dim_Vehiculo ---
    print("Creando Dim_Vehiculo...")
    dim_vehiculo = pd.DataFrame({
        'id_vehiculo': [1, 2, 3, 4],
        'nombre_vehiculo': ['articulado', 'padron', 'complementario', 'auxiliar']
    })

    print("Creando Dim_Tipo_Evento...")
    dim_tipo_evento = pd.DataFrame({
        'id_tipo_evento': [1, 2, 3, 4, 5, 6, 7, 8, 9],
        'nombre_evento': [
            'certificacion', 
            'reactivacion', 
            'renovacion', 
            'observacion', 
            'restriccion medica', 
            'suspension', 
            'cancelacion',
            'advertencia',
            'condicionamiento'
        ]
    })
    dim_tipo_evento['id_vigencia'] = id_vigencia_default
    
    tipo_evento_map = dict(zip(dim_tipo_evento['nombre_evento'], dim_tipo_evento['id_tipo_evento']))

    # --- 4. Dim_Perfil_Tipologia ---
    print("Creando Dim_Perfil_Tipologia...")
    col_tipologia = [c for c in df.columns if 'TIPOLOGIA' in c.upper()]
    
    if col_tipologia:
        tipologias_unicas = df[col_tipologia[0]].dropna().unique()
        perfiles = []
        for t in tipologias_unicas:
            try:
                # Extraemos el numero (convirtiendo el string o float) para aplicar reglas verdaderas
                t_val = int(float(t))
            except ValueError:
                t_val = -1
                
            perfiles.append({
                'id_perfil_tipologia': t,
                'autoriza_articulado': t_val == 1,
                'autoriza_padron': t_val in [1, 2],
                'autoriza_complementario': t_val in [1, 2, 3],
                'autoriza_auxiliar': t_val == 4,
                'id_vigencia': id_vigencia_default
            })
            
        dim_perfil_tipologia = pd.DataFrame(perfiles)
        df = df.merge(dim_perfil_tipologia[['id_perfil_tipologia']], left_on=col_tipologia[0], right_on='id_perfil_tipologia', how='left')
    else:
        dim_perfil_tipologia = pd.DataFrame(columns=['id_perfil_tipologia', 'autoriza_articulado', 'autoriza_padron', 'autoriza_complementario', 'autoriza_auxiliar', 'id_vigencia'])
        df['id_perfil_tipologia'] = np.nan

    # --- 5. Dim_Persona ---
    print("Creando Dim_Persona...")
    col_cedula = [c for c in df.columns if 'CEDULA' in c.upper() or 'DOCUMENTO' in c.upper()][0] if [c for c in df.columns if 'CEDULA' in c.upper() or 'DOCUMENTO' in c.upper()] else None
    if not col_cedula:
        col_cedula = col_codigo
        
    otras_cols_persona = [c for c in df.columns if any(x in c.upper() for x in ['NOMBRES', 'APELLIDO', 'CEDULA', 'DOCUMENTO', 'GENERO', 'NACIMIENTO'])]
    
    dim_persona = df[otras_cols_persona].copy().drop_duplicates(subset=[col_cedula])
    dim_persona['id_vigencia'] = id_vigencia_default
    
    def format_persona_column(c):
        if ' - ' in c:
            c = c.split(' - ')[-1]
        return to_snake_case(c)
    
    dim_persona.rename(columns=format_persona_column, inplace=True)
    id_persona_col = format_persona_column(col_cedula)
    dim_persona.rename(columns={id_persona_col: 'id_persona'}, inplace=True)

    # Reorder columns to put id_persona first
    cols_persona = dim_persona.columns.tolist()
    if 'id_persona' in cols_persona:
        cols_persona.insert(0, cols_persona.pop(cols_persona.index('id_persona')))
        dim_persona = dim_persona[cols_persona]

    for col in dim_persona.columns:
        if dim_persona[col].dtype == 'object':
            dim_persona[col] = dim_persona[col].apply(
                lambda x: str(x).strip().title() if pd.notna(x) and isinstance(x, str) else x
            )

    # --- 5b. Dim_Codigo ---
    print("Creando Dim_Codigo...")
    cols_codigo_attr = [col_codigo, col_cedula, 'id_empresa', 'id_perfil_tipologia']
        
    dim_codigo = df[cols_codigo_attr].copy().drop_duplicates(subset=[col_codigo])
    dim_codigo['id_vigencia'] = id_vigencia_default
    
    def format_codigo_column(c):
        if ' - ' in c:
            c = c.split(' - ')[-1]
        return to_snake_case(c)
        
    dim_codigo.rename(columns=format_codigo_column, inplace=True)
    dim_codigo.rename(columns={
        format_codigo_column(col_codigo): 'id_codigo',
        format_codigo_column(col_cedula): 'id_persona'
    }, inplace=True)

    # --- 6. Fact_Licencias ---
    print("Creando Fact_Licencias...")
    cols_licencia = [c for c in df.columns if 'LICENCIA' in c.upper()]
    if cols_licencia:
        fact_licencias = df[[col_codigo] + cols_licencia].copy()
        fact_licencias.dropna(subset=cols_licencia, how='all', inplace=True)
        fact_licencias.insert(0, 'id_hecho_licencia', range(1, len(fact_licencias) + 1))
        fact_licencias['id_vigencia'] = id_vigencia_default
        fact_licencias.rename(columns=lambda x: 'id_codigo' if x == col_codigo else to_snake_case(x.split(' - ')[-1] if ' - ' in x else x), inplace=True)
        if 'estado' in fact_licencias.columns:
            fact_licencias.drop(columns=['estado'], inplace=True)
    else:
        fact_licencias = pd.DataFrame()

    # --- 7. Dim_Tipo_Evento y Fact_Eventos_Operador ---
    print("Creando Dim_Tipo_Evento y Fact_Eventos_Operador...")
    eventos = []
    
    for _, row in df.iterrows():
        id_operador = row[col_codigo]
        if pd.isna(id_operador):
            continue
            
        operator_events = {}
            
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                continue
                
            info_evento = classify_event_column(col)
            if info_evento:
                nombre_evento, vehiculo, intento, atributo = info_evento
                
                event_key = (nombre_evento, vehiculo, intento)
                if event_key not in operator_events:
                    operator_events[event_key] = {}
                operator_events[event_key][atributo] = val
                
        for (nombre_evento, vehiculo, intento), attrs in operator_events.items():
            id_tipo = tipo_evento_map.get(nombre_evento)
            if not id_tipo:
                continue
                
            row_dict = {
                'id_codigo': id_operador,
                'id_tipo_evento': id_tipo,
                'id_vehiculo_evaluado': vehiculo
            }
            row_dict.update(attrs)
            if id_tipo in [4, 8, 9]:
                row_dict.setdefault('FECHA OBSERVACION', None)
            eventos.append(row_dict)
                
    df_eventos_raw = pd.DataFrame(eventos)
    
    if not df_eventos_raw.empty:
        fact_eventos = df_eventos_raw.copy()
        
        # Reordenar para que id_codigo y id_tipo_evento queden de primeros
        cols = fact_eventos.columns.tolist()
        cols.insert(0, cols.pop(cols.index('id_tipo_evento')))
        cols.insert(0, cols.pop(cols.index('id_codigo')))
        
        # Mover observacion al final antes de id_vigencia
        if 'OBSERVACION' in cols:
            cols.append(cols.pop(cols.index('OBSERVACION')))
            
        fact_eventos = fact_eventos[cols]
        
        fact_eventos.insert(0, 'id_hecho_evento', range(1, len(fact_eventos) + 1))
        fact_eventos['id_vigencia'] = id_vigencia_default
    else:
        fact_eventos = pd.DataFrame()

    # --- Aplicar snake_case (RAYA AL PISO) y limpiar datos problemáticos ---
    fecha_hoy = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    for df_out in [dim_vigencia, dim_empresa, dim_vehiculo, dim_perfil_tipologia, dim_persona, dim_codigo, fact_licencias, dim_tipo_evento, fact_eventos]:
        if not df_out.empty:
            df_out['fecha_registro'] = fecha_hoy
            df_out['usuario_registra'] = 'sistema'
            df_out.columns = [to_snake_case(c) for c in df_out.columns]
            # Limpiar TODAS las columnas de texto (cubriendo object, string y str de pyarrow)
            for col in df_out.columns:
                if str(df_out[col].dtype) in ['object', 'string', 'str']:
                    df_out[col] = df_out[col].apply(
                        lambda x: str(x).replace('\r\n', ' --- ').replace('\n', ' --- ').replace('\r', ' --- ').replace(',', ' ').replace(';', ' ').replace('"', '').strip() if pd.notna(x) else x
                    )
            for col in df_out.columns:
                if df_out[col].dtype == 'float64':
                    try:
                        if df_out[col].dropna().apply(lambda x: x.is_integer()).all():
                            df_out[col] = df_out[col].astype('Int64')
                    except Exception:
                        pass

    # --- EXPORTAR ---
    out_dir = "Modelo_Estrella_Final_CSVs"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    print(f"Exportando tablas a la carpeta '{out_dir}'...")
    dim_vigencia.to_csv(os.path.join(out_dir, 'dim_vigencia_registro.csv'), index=False, encoding='utf-8-sig')
    dim_empresa.to_csv(os.path.join(out_dir, 'dim_empresa.csv'), index=False, encoding='utf-8-sig')
    dim_vehiculo.to_csv(os.path.join(out_dir, 'dim_vehiculo.csv'), index=False, encoding='utf-8-sig')
    dim_perfil_tipologia.to_csv(os.path.join(out_dir, 'dim_perfil_tipologia.csv'), index=False, encoding='utf-8-sig')
    dim_persona.to_csv(os.path.join(out_dir, 'dim_persona.csv'), index=False, encoding='utf-8-sig')
    dim_codigo.to_csv(os.path.join(out_dir, 'dim_codigo.csv'), index=False, encoding='utf-8-sig')
    
    if not fact_licencias.empty:
        fact_licencias.to_csv(os.path.join(out_dir, 'fact_licencias.csv'), index=False, encoding='utf-8-sig')
    
    if not dim_tipo_evento.empty:
        dim_tipo_evento.to_csv(os.path.join(out_dir, 'dim_tipo_evento.csv'), index=False, encoding='utf-8-sig')
        fact_eventos.to_csv(os.path.join(out_dir, 'fact_eventos_operador.csv'), index=False, encoding='utf-8-sig')
        
    print("¡Proceso completado exitosamente! Modelo de Estrella MAESTRO generado.")

if __name__ == '__main__':
    main()
