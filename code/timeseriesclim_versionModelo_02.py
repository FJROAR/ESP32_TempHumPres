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

df = pd.read_excel("../data/estacion.xlsx")

# Renombrar a nombres del modelo
df = df.rename(columns={
    "date": "datetime",
    "tavg": "temp",
    "prcp": "rain_raw",
    "pres": "pressure"}
    )

# Formato fecha
df["datetime"] = pd.to_datetime(df["datetime"])

# Filtrar rango
df = df[(df["datetime"] >= "2026-02-22") & 
        (df["datetime"] <= "2026-04-17")].copy()

# Fechas diarias
df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")

# Target: lluvia
df["target"] = (df["rain_raw"] > 0).astype(int)


###############################################################################
#                 Visualización de la información                             #
###############################################################################

df = df.sort_values("datetime")

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=df["datetime"],
    y=df["temp"],
    mode="lines",
    line=dict(width=2),
    name="temp"
))
fig1.update_layout(xaxis_title="Día con hora", yaxis_title="Temperatura")
fig1.show()

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df["datetime"],
    y=df["pressure"],
    mode="lines",
    line=dict(width=2),
    name="pressure"
))
fig2.update_layout(xaxis_title="Día con hora", yaxis_title="Presión")
fig2.show()




###############################################################################
#         Tratamiento de variable. Conversión a hora                          #
###############################################################################

df_day = df[["date", "temp", "pressure", "target"]].copy()

df_day = df_day.rename(columns={
    "temp": "tmean",
    "pressure": "pmean"}
    )

# Lags
df_day["tmean_l1"] = df_day["tmean"].shift(1)
df_day["pmean_l1"] = df_day["pmean"].shift(1)

# Tendencia presión
df_day["p_diff"] = df_day["pmean"].shift(1) - df_day["pmean"].shift(2)



###############################################################################
#     Dataset final: En este caso la target se calculó al principio           #
###############################################################################

df_model = df_day.dropna().reset_index(drop=True)

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
#             Selección de variables en la regresión lineal                   #
###############################################################################

cols = [
    #"tmean_l1",
    "pmean_l1"#,
    #"p_diff"
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

y_pred_logit = result.predict(X_test_sm)



###############################################################################
# 7. Decision Tree
###############################################################################

dt = DecisionTreeClassifier(max_depth=3, random_state=42)
dt.fit(X_train[cols], y_train)

y_pred_dt = dt.predict_proba(X_test[cols])[:, 1]

print(export_text(dt, feature_names=cols))

###############################################################################
# 8. Random Forest
###############################################################################

rf = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
rf.fit(X_train[cols], y_train)

y_pred_rf = rf.predict_proba(X_test[cols])[:, 1]

###############################################################################
# 9. Resultados
###############################################################################

df_pred = pd.DataFrame({
    "date": df_model.iloc[split:]["date"].values,
    "real": y_test.values,
    "logit": y_pred_logit,
    "tree": y_pred_dt,
    "rf": y_pred_rf
})

print(df_pred)