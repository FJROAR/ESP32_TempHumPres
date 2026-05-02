import pandas as pd
import plotly.io as pio
import plotly.graph_objects as go
pio.renderers.default = "browser"
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import export_text, DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


###############################################################################
#         Lectura de datgos a partir del 22 de 02                             #
###############################################################################

df = pd.read_csv("../data/clim28033.txt",
                 header=None,
                 skiprows=1,
                 names=["date", "hour", "temp", "humid", "pressure"])

df["datetime"] = pd.to_datetime(df["date"].astype(str) + " " + df["hour"], errors="coerce")

df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
df["humid"] = pd.to_numeric(df["humid"], errors="coerce")
df["pressure"] = pd.to_numeric(df["pressure"], errors="coerce")

df = df.dropna()

df = df[df["datetime"] >= "2026-02-22"].copy()



###############################################################################
#                 Visualización de la información                             #
###############################################################################

df_hourly = df.set_index("datetime").resample("h").mean(numeric_only=True).reset_index()

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_hourly["datetime"], y=df_hourly["temp"], name="temp"))
fig1.update_layout(xaxis_title="Date", yaxis_title="Temperatura")
fig1.show()

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_hourly["datetime"], y=df_hourly["humid"], name="humid"))
fig2.update_layout(xaxis_title="Date", yaxis_title="Humedad")
fig2.show()

fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=df_hourly["datetime"], y=df_hourly["pressure"], name="pressure"))
fig3.update_layout(xaxis_title="Date", yaxis_title="Presión")
fig3.show()


###############################################################################
#         Tratamiento de variable. Conversión a hora                          #
###############################################################################

df["hour_group"] = df["datetime"].dt.floor("h")

def hourly_processing(group):
    if len(group) < 3:
        return None
    idx_max = group["temp"].idxmax()
    idx_min = group["temp"].idxmin()
    group = group.drop([idx_max, idx_min])
    return pd.Series({
        "date": group["hour_group"].iloc[0].date(),
        "hour": group["hour_group"].iloc[0].hour,
        "temp": group["temp"].mean(),
        "humid": group["humid"].mean(),
        "pressure": group["pressure"].mean()
    })

df_hour = df.groupby("hour_group").apply(hourly_processing).dropna().reset_index(drop=True)

df_hour["datetime"] = pd.to_datetime(
    df_hour["date"].astype(str) + " " + df_hour["hour"].astype(str) + ":00:00")

#Target: Se toma de los datos oficiales

df_target = pd.read_excel("../data/lluvia.xlsx")
df_target["date"] = pd.to_datetime(df_target["date"].astype(str),
                                   format="%Y%m%d").dt.strftime("%Y-%m-%d")
df_target["rain"] = pd.to_numeric(df_target["rain"], errors="coerce")
df_target["target"] = (df_target["rain"] > 0.5).astype(int)
df_target = df_target[["date", "target"]]


# Construcción de variables con infomración del día anterior

df_hour["date"] = df_hour["datetime"].dt.strftime("%Y-%m-%d")

df_day = df_hour.groupby("date").agg(
    tmean=("temp", "mean"),
    hmean=("humid", "mean"),
    pmean=("pressure", "mean"),
    pmax=("pressure", "max"),
    pmin=("pressure", "min")).reset_index()

# Variables clave (menos colinealidad)
df_day["pvar"] = df_day["pmax"] - df_day["pmin"]

# Lags
df_day["tmean_l1"] = df_day["tmean"].shift(1)
df_day["hmean_l1"] = df_day["hmean"].shift(1)
df_day["pmean_l1"] = df_day["pmean"].shift(1)
df_day["pvar_l1"] = df_day["pvar"].shift(1)

# Diferencias de presión diarias
df_day["p_diff"] = df_day["pmean"].shift(1) - df_day["pmean"].shift(2)

df_var = df_day[[
    "date",
    "tmean_l1",
    "hmean_l1",
    "pmean_l1",
    "pvar_l1",
    "p_diff"
    ]].dropna().reset_index(drop=True)


###############################################################################
#     Dataset final: En este caso la target se calculó al principio           #
###############################################################################

df_model = pd.merge(df_target, df_var, on="date")

X = df_model.drop(columns=["date", "target"])
y = df_model["target"]

# Split temporal
n = len(X)
split = int(n * 0.9)

X_train = X.iloc[:split]
X_test  = X.iloc[split:]
y_train = y.iloc[:split]
y_test  = y.iloc[split:]


###############################################################################
#                        Selección de variables                               # 
###############################################################################

cols = ['tmean_l1', 
        'hmean_l1', 
        'pmean_l1', 
        #'pvar_l1', 
        #'p_diff'
        ]

###############################################################################
#                       Escalado de variables                                 #
###############################################################################

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train[cols])
X_test_scaled  = scaler.transform(X_test[cols])


###############################################################################
#                      Regresión logística                                    #
###############################################################################

X_train_sm = pd.DataFrame(X_train_scaled, columns=cols, index=X_train.index)
X_test_sm  = pd.DataFrame(X_test_scaled,  columns=cols, index=X_test.index)

X_train_sm = sm.add_constant(X_train_sm)
X_test_sm  = sm.add_constant(X_test_sm)

model = sm.Logit(y_train, X_train_sm)
result = model.fit()

print(result.summary())

# Predicción
y_pred_logit = result.predict(X_test_sm)

# ======================================
# 8. Decision Tree
# ======================================

dt = DecisionTreeClassifier(max_depth=3, random_state=42)
dt.fit(X_train, y_train)
y_pred_dt = dt.predict_proba(X_test)[:, 1]

print(export_text(dt, feature_names=list(X_train.columns)))

# ======================================
# 9. Random Forest
# ======================================

rf = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict_proba(X_test)[:, 1]

# ======================================
# 10. Resultados
# ======================================

df_pred = pd.DataFrame({
    "date": df_model.iloc[split:]["date"].values,
    "real": y_test.values,
    "logit": y_pred_logit,
    "tree": y_pred_dt,
    "rf": y_pred_rf
})

print(df_pred)