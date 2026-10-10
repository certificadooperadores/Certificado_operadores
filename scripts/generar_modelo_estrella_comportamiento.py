import pandas as pd
import numpy as np
import os
import re
import unicodedata
import tempfile
import shutil
import datetime

def limpiar_fecha_series(series):
    dt = pd.to_datetime(series, dayfirst=True, errors='coerce')
    return dt.dt.strftime('%Y-%m-%d')

def limpiar_hora_series(series):
    def convert_fraction(x):
        if pd.isna(x): return x
        s = str(x).strip()
        if not s or s.lower() in ['nan', 'none', 'null', 'n.a', 'no aporta', '0']:
            return np.nan
        try:
            val_f = float(s)
            if 0 <= val_f < 1.0:
                tot_sec = int(round(val_f * 86400))
                h = (tot_sec // 3600) % 24
                m = (tot_sec % 3600) // 60
                sec = tot_sec % 60
                return f"{h:02d}:{m:02d}:{sec:02d}"
        except Exception:
            pass
        return s

    s_hora = series.apply(convert_fraction)
    dt_hora = pd.to_datetime(s_hora, format='%H:%M:%S', errors='coerce')
    mask_null = dt_hora.isna() & s_hora.notna()
    if mask_null.any():
        dt_hm = pd.to_datetime(s_hora[mask_null], format='%H:%M', errors='coerce')
        dt_hora.update(dt_hm)
        mask_still = dt_hora.isna() & s_hora.notna()
        if mask_still.any():
            dt_gen = pd.to_datetime(s_hora[mask_still], errors='coerce')
            dt_hora.update(dt_gen)

    return dt_hora.dt.strftime('%H:%M:%S')

def limpiar_id_codigo_series(series):
    s_num = pd.to_numeric(series, errors='coerce')
    mask_valid = s_num.notna() & (s_num >= 10000) & (s_num <= 99999) & (s_num == s_num.round())
    s_clean = pd.Series(np.nan, index=series.index, dtype='Int64')
    s_clean[mask_valid] = s_num[mask_valid].astype('Int64')
    return s_clean

def limpiar_entero_series(series):
    s_num = pd.to_numeric(series, errors='coerce')
    mask_valid = s_num.notna() & (s_num == s_num.round())
    s_clean = pd.Series(np.nan, index=series.index, dtype='Int64')
    s_clean[mask_valid] = s_num[mask_valid].astype('Int64')
    return s_clean

def limpiar_sitio_texto_series(series):
    def clean_val(val):
        if pd.isna(val) or val is None:
            return np.nan
            
        dt = None
        if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
            dt = val
        else:
            val_str = str(val).strip()
            if not val_str or val_str.lower() in ['nan', 'none', 'null', '0']:
                return np.nan
            if re.search(r'^\d{4}-\d{2}-\d{2}', val_str) or re.search(r'^\d{1,2}/\d{1,2}/\d{2,4}', val_str):
                try:
                    parsed = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
                    if not pd.isna(parsed):
                        dt = parsed
                except Exception:
                    pass

        if dt is not None and not pd.isna(dt):
            month_abbrs = {
                1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
                7: 'JUL', 8: 'AGO', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC'
            }
            day = dt.day
            month_str = month_abbrs.get(dt.month, '')
            year_suffix = dt.year % 100
            return f"{day}{month_str}{year_suffix}"

        val_str = str(val).strip()
        if val_str.endswith('.0'):
            val_str = val_str[:-2]
        return limpiar_texto(val_str)

    return series.apply(clean_val)

def to_snake_case(name):
    if not isinstance(name, str):
        return name
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    name = re.sub(r'[^a-zA-Z0-9]', ' ', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name.lower()

def limpiar_texto(val):
    if pd.isna(val) or val is None:
        return val
    if isinstance(val, str):
        val = val.replace('\r\n', ' --- ').replace('\n', ' --- ').replace('\r', ' --- ').replace('\t', ' ')
        val = val.replace(',', ' ').replace(';', ' ').replace('"', '').strip()
        val = re.sub(r'\s+', ' ', val)
    return val

def normalizar_para_busqueda(text):
    if pd.isna(text) or text is None:
        return ""
    text_str = str(text).strip()
    if text_str.endswith('.0'):
        text_str = text_str[:-2]
    if not text_str or text_str.lower() in ['nan', 'none', 'null']:
        return ""
    text_nfd = ''.join(c for c in unicodedata.normalize('NFD', text_str) if unicodedata.category(c) != 'Mn')
    cleaned = re.sub(r'[^a-zA-Z0-9]', ' ', text_nfd)
    cleaned = re.sub(r'\s+', ' ', cleaned.strip().lower())
    return cleaned

def find_col(df_cols, possible_names):
    for p in possible_names:
        p_clean = re.sub(r'\s+', ' ', p.lower().replace('\n', ' ').replace('\r', ' ').strip())
        for col in df_cols:
            col_clean = re.sub(r'\s+', ' ', str(col).lower().replace('\n', ' ').replace('\r', ' ').strip())
            if p_clean == col_clean:
                return col
    return None

import subprocess

def copy_excel_force(file_path):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_{os.path.basename(file_path)}")
    cmd = f'powershell -Command "Copy-Item -Path \'{file_path}\' -Destination \'{temp_path}\' -Force"'
    subprocess.run(cmd, shell=True, capture_output=True)
    return temp_path

def read_excel_safe(file_path, sheet_name=None):
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except PermissionError:
        temp_path = copy_excel_force(file_path)
        return pd.read_excel(temp_path, sheet_name=sheet_name)

def get_excel_sheets_safe(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        return xls.sheet_names
    except PermissionError:
        temp_path = copy_excel_force(file_path)
        xls = pd.ExcelFile(temp_path)
        return xls.sheet_names

def to_csv_safe(df, file_path):
    try:
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
    except PermissionError:
        print(f"Advertencia: No se pudo sobrescribir '{file_path}' porque está abierto en otro programa. Intentando reemplazar...")
        base, ext = os.path.splitext(file_path)
        alt_path = f"{base}_actualizado{ext}"
        df.to_csv(alt_path, index=False, encoding='utf-8-sig')
        print(f"Archivo guardado como: '{alt_path}'")

def main():
    base_dir = r'C:\Users\maortiz\OneDrive - metrocali.gov.co\Scripts\Proyecto_BD_operadores\Archivos_excel_iniciales\Comportamiento'
    out_dir = r'C:\Users\maortiz\OneDrive - metrocali.gov.co\Scripts\Proyecto_BD_operadores\Modelo_Estrella_Final_CSVs'
    
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    archivo_auxiliares = os.path.join(base_dir, 'auxiliares_reporte.xlsx')
    if not os.path.exists(archivo_auxiliares):
        print(f"Error: El archivo {archivo_auxiliares} no existe.")
        return

    print("1. Leyendo dimensiones de auxiliares_reporte.xlsx...")
    fecha_hoy = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    id_vigencia_default = 1

    # --- 1. Dim Impacto ---
    print("  - Procesando dim_impacto...")
    df_impacto = read_excel_safe(archivo_auxiliares, sheet_name='dim_impacto')
    df_impacto.dropna(how='all', inplace=True)
    df_impacto.columns = [to_snake_case(c) for c in df_impacto.columns]
    df_impacto['fecha_registro'] = fecha_hoy
    df_impacto['usuario_registra'] = 'sistema'

    # --- 2. Dim Comportamiento ---
    print("  - Procesando dim_comportamiento...")
    df_comportamiento = read_excel_safe(archivo_auxiliares, sheet_name='dim_comportamiento')
    df_comportamiento.dropna(how='all', inplace=True)
    df_comportamiento.columns = [to_snake_case(c) for c in df_comportamiento.columns]
    df_comportamiento['fecha_registro'] = fecha_hoy
    df_comportamiento['usuario_registra'] = 'sistema'

    # --- 3. Dim Detalle Comportamiento ---
    print("  - Procesando dim_detalle_comportamiento...")
    df_det_comportamiento = read_excel_safe(archivo_auxiliares, sheet_name='dim_detalle_comportamiento')
    df_det_comportamiento.dropna(how='all', inplace=True)
    df_det_comportamiento.columns = [to_snake_case(c) for c in df_det_comportamiento.columns]
    if 'id_impacto' in df_det_comportamiento.columns and 'id_comportamiento' not in df_det_comportamiento.columns:
        df_det_comportamiento.rename(columns={'id_impacto': 'id_comportamiento'}, inplace=True)
        print("    - Columna 'id_impacto' renombrada a 'id_comportamiento' (nomenclatura del source)")
    df_det_comportamiento['fecha_registro'] = fecha_hoy
    df_det_comportamiento['usuario_registra'] = 'sistema'

    # Mapeos vectorizados
    col_desc_det = [c for c in df_det_comportamiento.columns if 'descrip' in c][0]
    df_det_comportamiento['norm_key'] = df_det_comportamiento[col_desc_det].apply(normalizar_para_busqueda)
    
    valid_det = df_det_comportamiento[df_det_comportamiento['norm_key'] != ""]
    id_jerarquia_map = dict(zip(valid_det['norm_key'], valid_det['id_jerarquia']))
    fuente_map = dict(zip(valid_det['norm_key'], valid_det['fuente']))

    # Mapeo Cédula -> id_codigo desde dim_codigo.csv / dim_persona
    cedula_to_codigo_map = {}
    archivo_dim_codigo = os.path.join(out_dir, 'dim_codigo.csv')
    if os.path.exists(archivo_dim_codigo):
        try:
            df_dim_cod = pd.read_csv(archivo_dim_codigo, low_memory=False)
            df_dim_cod['ced_clean'] = pd.to_numeric(df_dim_cod['id_persona'], errors='coerce').astype('Int64')
            df_dim_cod['cod_clean'] = pd.to_numeric(df_dim_cod['id_codigo'], errors='coerce').astype('Int64')
            cedula_to_codigo_map = dict(zip(df_dim_cod['ced_clean'].dropna(), df_dim_cod['cod_clean'].dropna()))
            print(f"  - Mapeo Cédula -> id_codigo cargado desde dim_codigo.csv ({len(cedula_to_codigo_map)} registros).")
        except Exception as e:
            print(f"  - Advertencia al cargar dim_codigo.csv: {e}")

    # Estructura final de fact_comportamiento
    target_cols = [
        'id_jerarquia', 'fuente', 'descripcion_comportamiento', 'caso_bitacora_ticket',
        'fecha_evento', 'nota', 'vehiculo', 'viaje', 'tarea', 'hora_evento',
        'id_codigo', 'ruta', 'sitio_salida', 'sitio_novedad', 'numero_lesionados',
        'observacion_concesionario', 'respuesta_mc', 'responsable_pqrs_cot',
        'direccion_infraccion', 'clase_servicio', 'tipo_servicio', 'fuente_infraccion', 'placa'
    ]

    dfs_fact = []

    # --- ARCHIVO 1: Gestión del Certificado de Idoneidad del Operador.xlsx ---
    file1_path = os.path.join(base_dir, 'Gestión del Certificado de Idoneidad del Operador.xlsx')
    if os.path.exists(file1_path):
        print("  - Leyendo Gestión del Certificado de Idoneidad del Operador.xlsx...")
        sheets1 = get_excel_sheets_safe(file1_path)
        sheet1_candidates = [s for s in sheets1 if '2014' in s.lower() or 'hoy' in s.lower()]
        sheet1 = sheet1_candidates[0] if sheet1_candidates else sheets1[0]
        df1 = read_excel_safe(file1_path, sheet_name=sheet1)
        df1.dropna(how='all', inplace=True)

        c_desc = find_col(df1.columns, ['Jerarquía', 'Jerarquia'])
        df1['norm_key'] = df1[c_desc].apply(normalizar_para_busqueda) if c_desc else ""
        
        df1_mapped = pd.DataFrame()
        df1_mapped['id_jerarquia'] = df1['norm_key'].map(id_jerarquia_map)
        df1_mapped['fuente'] = df1['norm_key'].map(fuente_map)
        df1_mapped['descripcion_comportamiento'] = df1[c_desc] if c_desc else np.nan
        df1_mapped['caso_bitacora_ticket'] = df1[find_col(df1.columns, ['No Caso', 'No\nCaso', 'No. Caso'])] if find_col(df1.columns, ['No Caso', 'No\nCaso', 'No. Caso']) else np.nan
        df1_mapped['fecha_evento'] = df1[find_col(df1.columns, ['Fecha Bitácora', 'Fecha\nBitácora', 'Fecha Bitacora'])] if find_col(df1.columns, ['Fecha Bitácora', 'Fecha\nBitácora', 'Fecha Bitacora']) else np.nan
        df1_mapped['nota'] = df1[find_col(df1.columns, ['Nota', 'Descripción o Nota', 'Descripcion o Nota'])] if find_col(df1.columns, ['Nota', 'Descripción o Nota', 'Descripcion o Nota']) else np.nan
        df1_mapped['vehiculo'] = df1[find_col(df1.columns, ['Vehículo', 'Vehiculo'])] if find_col(df1.columns, ['Vehículo', 'Vehiculo']) else np.nan
        df1_mapped['viaje'] = df1[find_col(df1.columns, ['Viaje'])] if find_col(df1.columns, ['Viaje']) else np.nan
        df1_mapped['tarea'] = df1[find_col(df1.columns, ['Tarea'])] if find_col(df1.columns, ['Tarea']) else np.nan
        df1_mapped['hora_evento'] = df1[find_col(df1.columns, ['Hora Evento', 'Hora\nEvento'])] if find_col(df1.columns, ['Hora Evento', 'Hora\nEvento']) else np.nan
        df1_mapped['id_codigo'] = df1[find_col(df1.columns, ['Código Operador', 'Código\nOperador', 'Codigo Operador'])] if find_col(df1.columns, ['Código Operador', 'Código\nOperador', 'Codigo Operador']) else np.nan
        df1_mapped['ruta'] = df1[find_col(df1.columns, ['Ruta'])] if find_col(df1.columns, ['Ruta']) else np.nan
        df1_mapped['sitio_salida'] = df1[find_col(df1.columns, ['Sitio Salida', 'Sitio\nSalida'])] if find_col(df1.columns, ['Sitio Salida', 'Sitio\nSalida']) else np.nan
        df1_mapped['sitio_novedad'] = df1[find_col(df1.columns, ['Sitio Novedad', 'Sitio\nNovedad'])] if find_col(df1.columns, ['Sitio Novedad', 'Sitio\nNovedad']) else np.nan
        df1_mapped['numero_lesionados'] = np.nan
        df1_mapped['observacion_concesionario'] = df1[find_col(df1.columns, ['Observación Concesionario', 'Observacion Concesionario'])] if find_col(df1.columns, ['Observación Concesionario', 'Observacion Concesionario']) else np.nan
        df1_mapped['respuesta_mc'] = df1[find_col(df1.columns, ['Respuesta Metrocali', 'Respuesta\nMetrocali'])] if find_col(df1.columns, ['Respuesta Metrocali', 'Respuesta\nMetrocali']) else np.nan
        df1_mapped['responsable_pqrs_cot'] = np.nan
        df1_mapped['direccion_infraccion'] = np.nan
        df1_mapped['clase_servicio'] = np.nan
        df1_mapped['tipo_servicio'] = np.nan
        df1_mapped['fuente_infraccion'] = np.nan
        df1_mapped['placa'] = np.nan
        dfs_fact.append(df1_mapped[target_cols])

    # --- ARCHIVO 2: Accidentalidad Consolidada.xlsx ---
    file2_path = os.path.join(base_dir, 'Accidentalidad Consolidada.xlsx')
    if os.path.exists(file2_path):
        print("  - Leyendo Accidentalidad Consolidada.xlsx...")
        sheets2 = get_excel_sheets_safe(file2_path)
        sheet2 = [s for s in sheets2 if 'accidentalidad' in s.lower()][0]
        df2 = read_excel_safe(file2_path, sheet_name=sheet2)
        df2.dropna(how='all', inplace=True)

        c_desc = find_col(df2.columns, ['Jerarquía', 'Jerarquia'])
        df2['norm_key'] = df2[c_desc].apply(normalizar_para_busqueda) if c_desc else ""

        df2_mapped = pd.DataFrame()
        df2_mapped['id_jerarquia'] = df2['norm_key'].map(id_jerarquia_map)
        df2_mapped['fuente'] = df2['norm_key'].map(fuente_map)
        df2_mapped['descripcion_comportamiento'] = df2[c_desc] if c_desc else np.nan
        df2_mapped['caso_bitacora_ticket'] = df2[find_col(df2.columns, ['Caso'])] if find_col(df2.columns, ['Caso']) else np.nan
        df2_mapped['fecha_evento'] = df2[find_col(df2.columns, ['Fecha Bitácora', 'Fecha\nBitácora', 'Fecha Bitacora'])] if find_col(df2.columns, ['Fecha Bitácora', 'Fecha\nBitácora', 'Fecha Bitacora']) else np.nan
        df2_mapped['nota'] = df2[find_col(df2.columns, ['Nota'])] if find_col(df2.columns, ['Nota']) else np.nan
        df2_mapped['vehiculo'] = df2[find_col(df2.columns, ['Vehículo', 'Vehiculo'])] if find_col(df2.columns, ['Vehículo', 'Vehiculo']) else np.nan
        df2_mapped['viaje'] = df2[find_col(df2.columns, ['Viaje'])] if find_col(df2.columns, ['Viaje']) else np.nan
        df2_mapped['tarea'] = df2[find_col(df2.columns, ['Tarea'])] if find_col(df2.columns, ['Tarea']) else np.nan
        df2_mapped['hora_evento'] = df2[find_col(df2.columns, ['Hora Evento', 'Hora\nEvento'])] if find_col(df2.columns, ['Hora Evento', 'Hora\nEvento']) else np.nan
        df2_mapped['id_codigo'] = df2[find_col(df2.columns, ['Código Operador', 'Código\nOperador', 'Codigo Operador'])] if find_col(df2.columns, ['Código Operador', 'Código\nOperador', 'Codigo Operador']) else np.nan
        df2_mapped['ruta'] = df2[find_col(df2.columns, ['Ruta'])] if find_col(df2.columns, ['Ruta']) else np.nan
        df2_mapped['sitio_salida'] = df2[find_col(df2.columns, ['Sitio Salida', 'Sitio\nSalida'])] if find_col(df2.columns, ['Sitio Salida', 'Sitio\nSalida']) else np.nan
        df2_mapped['sitio_novedad'] = df2[find_col(df2.columns, ['Sitio Novedad', 'Sitio\nNovedad'])] if find_col(df2.columns, ['Sitio Novedad', 'Sitio\nNovedad']) else np.nan
        df2_mapped['numero_lesionados'] = df2[find_col(df2.columns, ['Número Lesionados', 'Número\nLesionados', 'Numero Lesionados'])] if find_col(df2.columns, ['Número Lesionados', 'Número\nLesionados', 'Numero Lesionados']) else np.nan
        df2_mapped['observacion_concesionario'] = df2[find_col(df2.columns, ['Observación Concesionario', 'Observacion Concesionario'])] if find_col(df2.columns, ['Observación Concesionario', 'Observacion Concesionario']) else np.nan
        df2_mapped['respuesta_mc'] = df2[find_col(df2.columns, ['Respuesta Metrocali', 'Respuesta\nMetrocali'])] if find_col(df2.columns, ['Respuesta Metrocali', 'Respuesta\nMetrocali']) else np.nan
        df2_mapped['responsable_pqrs_cot'] = np.nan
        df2_mapped['direccion_infraccion'] = np.nan
        df2_mapped['clase_servicio'] = np.nan
        df2_mapped['tipo_servicio'] = np.nan
        df2_mapped['fuente_infraccion'] = np.nan
        df2_mapped['placa'] = np.nan
        dfs_fact.append(df2_mapped[target_cols])

    # --- ARCHIVO 3: Consolidado Quejas Operadores.xlsx ---
    file3_path = os.path.join(base_dir, 'Consolidado Quejas Operadores.xlsx')
    if os.path.exists(file3_path):
        print("  - Leyendo Consolidado Quejas Operadores.xlsx...")
        sheets3 = get_excel_sheets_safe(file3_path)
        sheet3 = [s for s in sheets3 if 'consolidado' in s.lower()][0]
        df3 = read_excel_safe(file3_path, sheet_name=sheet3)
        df3.dropna(how='all', inplace=True)

        c_desc = find_col(df3.columns, ['Servicio'])
        df3['norm_key'] = df3[c_desc].apply(normalizar_para_busqueda) if c_desc else ""

        c_veh_num = find_col(df3.columns, ['Numero Vehiculo', 'Numero\nVehiculo'])
        c_veh_str = find_col(df3.columns, ['Vehiculo', 'Vehículo'])
        val_veh3 = df3[c_veh_num] if c_veh_num else (df3[c_veh_str] if c_veh_str else np.nan)

        df3_mapped = pd.DataFrame()
        df3_mapped['id_jerarquia'] = df3['norm_key'].map(id_jerarquia_map)
        df3_mapped['fuente'] = df3['norm_key'].map(fuente_map)
        df3_mapped['descripcion_comportamiento'] = df3[c_desc] if c_desc else np.nan
        df3_mapped['caso_bitacora_ticket'] = df3[find_col(df3.columns, ['Número deTicket', 'Número\ndeTicket', 'Numero deTicket'])] if find_col(df3.columns, ['Número deTicket', 'Número\ndeTicket', 'Numero deTicket']) else np.nan
        df3_mapped['fecha_evento'] = df3[find_col(df3.columns, ['Creado'])] if find_col(df3.columns, ['Creado']) else np.nan
        df3_mapped['nota'] = df3[find_col(df3.columns, ['Cuerpo'])] if find_col(df3.columns, ['Cuerpo']) else np.nan
        df3_mapped['vehiculo'] = val_veh3
        df3_mapped['viaje'] = np.nan
        df3_mapped['tarea'] = np.nan
        df3_mapped['hora_evento'] = np.nan
        df3_mapped['id_codigo'] = df3[find_col(df3.columns, ['Código Operador Implicado', 'Código\nOperador Implicado', 'Codigo Operador Implicado'])] if find_col(df3.columns, ['Código Operador Implicado', 'Código\nOperador Implicado', 'Codigo Operador Implicado']) else np.nan
        df3_mapped['ruta'] = np.nan
        df3_mapped['sitio_salida'] = np.nan
        df3_mapped['sitio_novedad'] = np.nan
        df3_mapped['numero_lesionados'] = np.nan
        df3_mapped['observacion_concesionario'] = np.nan
        df3_mapped['respuesta_mc'] = np.nan
        df3_mapped['responsable_pqrs_cot'] = df3[find_col(df3.columns, ['El implicado es responsable según COT?', 'El implicado es\nresponsable según COT?'])] if find_col(df3.columns, ['El implicado es responsable según COT?', 'El implicado es\nresponsable según COT?']) else np.nan
        df3_mapped['direccion_infraccion'] = np.nan
        df3_mapped['clase_servicio'] = np.nan
        df3_mapped['tipo_servicio'] = np.nan
        df3_mapped['fuente_infraccion'] = np.nan
        df3_mapped['placa'] = np.nan
        dfs_fact.append(df3_mapped[target_cols])

    # --- ARCHIVO 4: Consolidado Infracciones Operadores.xlsx ---
    file4_path = os.path.join(base_dir, 'Consolidado Infracciones Operadores.xlsx')
    if os.path.exists(file4_path):
        print("  - Leyendo Consolidado Infracciones Operadores.xlsx...")
        sheets4 = get_excel_sheets_safe(file4_path)
        sheet4 = [s for s in sheets4 if 'infracciones' in s.lower()][0]
        df4 = read_excel_safe(file4_path, sheet_name=sheet4)
        df4.dropna(how='all', inplace=True)

        c_desc = find_col(df4.columns, ['INFRACCIÓN', 'INFRACCION'])
        c_fecha = find_col(df4.columns, ['FECHA'])
        c_hora = find_col(df4.columns, ['HORA'])
        c_codigo = find_col(df4.columns, ['OPERADOR'])
        c_cedula4 = find_col(df4.columns, ['CEDULA', 'DOCUMENTO', 'CÉDULA'])
        c_nota4 = find_col(df4.columns, ['DESCRIPCIÓN INFRACCIÓN', 'DESCRIPCION INFRACCION', 'OBSERVACIÓN', 'OBSERVACION'])

        df4['norm_key'] = df4[c_desc].apply(normalizar_para_busqueda) if c_desc else ""

        # Mapeo id_codigo mediante CEDULA cruzada con dim_persona / dim_codigo
        if c_cedula4 and cedula_to_codigo_map:
            ced_series = pd.to_numeric(df4[c_cedula4], errors='coerce').astype('Int64')
            val_id_codigo4 = ced_series.map(cedula_to_codigo_map)
        else:
            val_id_codigo4 = df4[c_codigo] if c_codigo else np.nan

        df4_mapped = pd.DataFrame()
        df4_mapped['id_jerarquia'] = df4['norm_key'].map(id_jerarquia_map)
        df4_mapped['fuente'] = df4['norm_key'].map(fuente_map)
        df4_mapped['descripcion_comportamiento'] = df4[c_desc] if c_desc else np.nan
        df4_mapped['caso_bitacora_ticket'] = np.nan
        df4_mapped['fecha_evento'] = df4[c_fecha] if c_fecha else np.nan
        df4_mapped['nota'] = df4[c_nota4] if c_nota4 else np.nan
        df4_mapped['vehiculo'] = df4[find_col(df4.columns, ['MC'])] if find_col(df4.columns, ['MC']) else np.nan
        df4_mapped['viaje'] = np.nan
        df4_mapped['tarea'] = np.nan
        df4_mapped['hora_evento'] = df4[c_hora] if c_hora else np.nan
        df4_mapped['id_codigo'] = val_id_codigo4
        df4_mapped['ruta'] = np.nan
        df4_mapped['sitio_salida'] = np.nan
        df4_mapped['sitio_novedad'] = np.nan
        df4_mapped['numero_lesionados'] = np.nan
        df4_mapped['observacion_concesionario'] = np.nan
        df4_mapped['respuesta_mc'] = np.nan
        df4_mapped['responsable_pqrs_cot'] = np.nan
        df4_mapped['direccion_infraccion'] = df4[find_col(df4.columns, ['DIRECCIÓN', 'DIRECCION'])] if find_col(df4.columns, ['DIRECCIÓN', 'DIRECCION']) else np.nan
        df4_mapped['clase_servicio'] = df4[find_col(df4.columns, ['CLASE VEHÍCULO', 'CLASE VEHICULO'])] if find_col(df4.columns, ['CLASE VEHÍCULO', 'CLASE VEHICULO']) else np.nan
        df4_mapped['tipo_servicio'] = df4[find_col(df4.columns, ['TIPO SERVICIO'])] if find_col(df4.columns, ['TIPO SERVICIO']) else np.nan
        df4_mapped['fuente_infraccion'] = df4[find_col(df4.columns, ['TIPO'])] if find_col(df4.columns, ['TIPO']) else np.nan
        df4_mapped['placa'] = df4[find_col(df4.columns, ['PLACA'])] if find_col(df4.columns, ['PLACA']) else np.nan
        dfs_fact.append(df4_mapped[target_cols])

    print("3. Consolidando Fact_Comportamiento...")
    if dfs_fact:
        fact_comportamiento = pd.concat(dfs_fact, ignore_index=True)
    else:
        fact_comportamiento = pd.DataFrame(columns=target_cols)

    if not fact_comportamiento.empty:
        fact_comportamiento.insert(0, 'id_hecho_comportamiento', range(1, len(fact_comportamiento) + 1))
        fact_comportamiento['id_vigencia'] = id_vigencia_default
        fact_comportamiento['fecha_registro'] = fecha_hoy
        fact_comportamiento['usuario_registra'] = 'sistema'

    # --- Limpieza general y formato de columnas ---
    print("4. Aplicando limpieza de texto, snake_case y formateo final...")
    tablas = [
        ('dim_impacto', df_impacto),
        ('dim_comportamiento', df_comportamiento),
        ('dim_detalle_comportamiento', df_det_comportamiento),
        ('fact_comportamiento', fact_comportamiento)
    ]

    for nombre_tabla, df_out in tablas:
        if df_out.empty:
            continue
        if 'norm_key' in df_out.columns:
            df_out.drop(columns=['norm_key'], inplace=True)
        df_out.columns = [to_snake_case(c) for c in df_out.columns]
        for col in df_out.columns:
            if str(df_out[col].dtype) in ['object', 'string', 'str']:
                df_out[col] = df_out[col].apply(limpiar_texto)
            if col in ['vehiculo', 'viaje', 'tarea']:
                df_out[col] = limpiar_entero_series(df_out[col])
            elif col == 'id_codigo':
                df_out[col] = limpiar_id_codigo_series(df_out[col])
            elif col == 'fecha_evento':
                df_out[col] = limpiar_fecha_series(df_out[col])
            elif col == 'hora_evento':
                df_out[col] = limpiar_hora_series(df_out[col])
            elif col in ['sitio_salida', 'sitio_novedad']:
                df_out[col] = limpiar_sitio_texto_series(df_out[col])
            elif df_out[col].dtype == 'float64':
                try:
                    if df_out[col].dropna().apply(lambda x: float(x).is_integer()).all():
                        df_out[col] = df_out[col].astype('Int64')
                except Exception:
                    pass

    # --- Exportar CSVs ---
    print(f"5. Exportando tablas a '{out_dir}'...")
    to_csv_safe(df_impacto, os.path.join(out_dir, 'dim_impacto.csv'))
    to_csv_safe(df_comportamiento, os.path.join(out_dir, 'dim_comportamiento.csv'))
    to_csv_safe(df_det_comportamiento, os.path.join(out_dir, 'dim_detalle_comportamiento.csv'))
    if not fact_comportamiento.empty:
        to_csv_safe(fact_comportamiento, os.path.join(out_dir, 'fact_comportamiento.csv'))

    print("¡Proceso completado exitosamente! Modelo Estrella de Comportamiento generado.")

if __name__ == '__main__':
    main()
