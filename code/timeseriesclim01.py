import pandas as pd
import os
import glob
import plotly.io as pio
pio.renderers.default = "browser"
import plotly.express as px

# ======================================
# 1. Localización de carpetas
# ======================================

# Funciona en Spyder y ejecución normal
base_dir = os.getcwd()

# Si estamos dentro de /code, subir un nivel
if os.path.basename(base_dir) == "code":
    base_dir = os.path.dirname(base_dir)

data_dir = os.path.join(base_dir, "data")

# Buscar todos los archivos clim*.txt
files = glob.glob(os.path.join(data_dir, "clim*.txt"))

if len(files) == 0:
    raise FileNotFoundError(f"No se encontraron archivos clim*.txt en {data_dir}")

# ======================================
# 2. Lectura y creación de df
# ======================================

df_list = []

for file in files:
    temp_df = pd.read_csv(
        file,
        header=None,
        names=["date", "hour", "temp", "humid", "pressure"]
    )
    df_list.append(temp_df)

df = pd.concat(df_list, ignore_index=True)

# Conversión de tipos
df["datetime"] = pd.to_datetime(df["date"] + " " + df["hour"])
df["temp"] = df["temp"].astype(float)
df["humid"] = df["humid"].astype(float)
df["pressure"] = df["pressure"].astype(float)

# ======================================
# 3. Filtrar desde 2026-02-21 21:00
# ======================================

start_datetime = pd.to_datetime("2026-02-21 21:00:00")
df = df[df["datetime"] >= start_datetime].copy()

# ======================================
# 4. Crear dataset horario df_hour
# ======================================

df["hour_group"] = df["datetime"].dt.floor("H")

def hourly_processing(group):
    if len(group) < 3:
        return None
    
    idx_max = group["temp"].idxmax()
    idx_min = group["temp"].idxmin()
    
    group_filtered = group.drop([idx_max, idx_min])
    
    return pd.Series({
        "date": group["hour_group"].iloc[0].date(),
        "hour": group["hour_group"].iloc[0].hour,
        "temp": group_filtered["temp"].mean(),
        "humid": group_filtered["humid"].mean(),
        "pressure": group_filtered["pressure"].mean()
    })

df_hour = (
    df.groupby("hour_group")
      .apply(hourly_processing)
      .dropna()
      .reset_index(drop=True)
      )


# Asegurar eje temporal correcto
df_hour["datetime"] = pd.to_datetime(
    df_hour["date"].astype(str) + " " + df_hour["hour"].astype(str) + ":00:00"
)

# ==========================
# 1 Temperatura
# ==========================
fig_temp = px.line(df_hour, x="datetime", y="temp",
                   title="Evolución temporal de la Temperatura")
fig_temp.show()

# ==========================
# 2 Humedad
# ==========================
fig_humid = px.line(df_hour, x="datetime", y="humid",
                    title="Evolución temporal de la Humedad")
fig_humid.show()

# ==========================
# 3 Presión
# ==========================
fig_press = px.line(df_hour, x="datetime", y="pressure",
                    title="Evolución temporal de la Presión")
fig_press.show()