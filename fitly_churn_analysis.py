"""
fitly_churn_analysis.py

Objetivo:
- Ler os 3 arquivos CSV (account_info, customer_support, user_activity)
- Validar e limpar colunas (o básico + o que mais aparece na vida real)
- Padronizar chaves (customer_id)
- Criar métricas agregadas de engajamento (user_activity) e suporte (customer_support)
- Juntar tudo em uma tabela final (data mart) pronta para dashboard
- Exportar CSVs prontos para uso no Power BI / Tableau / Looker / Streamlit

Decisões (importantes pra prova):
- Eu NÃO apago linhas só por ter missing. Em dados reais isso acontece.
- Eu documento o que tratei e tento manter consistência.
- Eu corrijo “problemas estruturais” que impedem análise (ex.: chaves diferentes, churn_status Y/N etc.)

Correções implementadas (baseadas nos seus arquivos reais):
1) account_info tem 'churn_status' (Y/N) -> crio coluna 'churn' (0/1)
2) account_info NÃO tem 'signup_date' -> não invento coluna
3) support/activity usam user_id numérico; account usa customer_id com 'C' -> converto: 10125 -> C10125
4) support tem coluna 'state' 0/1 (não é estado dos EUA) -> renomeio para 'ticket_state_flag'
5) Evito erro do pd.qcut (muitos empates) -> crio 'engagement_quartile' de forma ROBUSTA
6) Corrijo warning futuro do pandas para had_support (uso dtype boolean)

Saídas:
- clean_account_info.csv
- clean_customer_support.csv
- clean_user_activity.csv
- fitly_dashboard_mart.csv
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd


# =========================
# 1) Configurações / caminhos
# =========================

ACCOUNT_PATH = "da_fitly_account_info.csv"
SUPPORT_PATH = "da_fitly_customer_support.csv"
ACTIVITY_PATH = "da_fitly_user_activity.csv"

OUT_ACCOUNT_CLEAN = "clean_account_info.csv"
OUT_SUPPORT_CLEAN = "clean_customer_support.csv"
OUT_ACTIVITY_CLEAN = "clean_user_activity.csv"
OUT_DASHBOARD_MART = "fitly_dashboard_mart.csv"


# =========================
# 2) Funções auxiliares
# =========================

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza nomes de colunas:
    - minúsculas
    - remove espaços extras
    - troca espaços por underscore
    - remove caracteres estranhos
    """
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    return df


US_STATE_TO_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new_hampshire": "NH", "new_jersey": "NJ", "new_mexico": "NM", "new_york": "NY",
    "north_carolina": "NC", "north_dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode_island": "RI",
    "south_carolina": "SC", "south_dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west_virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district_of_columbia": "DC"
}


def clean_account_state(value) -> str | None:
    """
    Estado (account_info.state) vem como nome (ex: 'New Jersey').
    Eu padronizo para sigla (NJ) porque fica mais limpo no dashboard.
    """
    if pd.isna(value):
        return None

    s = str(value).strip()
    if s == "" or s.lower() in {"na", "n/a", "none", "null"}:
        return None

    # "New Jersey" -> "new_jersey"
    key = s.lower().replace(" ", "_")
    return US_STATE_TO_ABBR.get(key, s.upper() if len(s) == 2 else s.title())


def clean_plan(value) -> str | None:
    """
    Normaliza plano: free/basic/pro/enterprise (esperado pela PM).
    Eu removo caracteres estranhos e deixo em minúsculo.
    """
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s == "" or s in {"na", "n/a", "none", "null"}:
        return None
    s = re.sub(r"[^a-z]", "", s)
    return s if s != "" else None


def churn_status_to_int(value) -> int | None:
    """
    Converte churn_status (Y/N) para churn (0/1).
    """
    if pd.isna(value):
        return None
    s = str(value).strip().lower()

    if s in {"y", "yes", "true", "1", "churn", "churned"}:
        return 1
    if s in {"n", "no", "false", "0", "active", "not_churned", "not churned"}:
        return 0
    return None


def safe_to_datetime(series: pd.Series) -> pd.Series:
    """
    Converte para datetime sem quebrar o pipeline (inválidos viram NaT).
    """
    return pd.to_datetime(series, errors="coerce")


def numeric_coerce(series: pd.Series) -> pd.Series:
    """
    Converte para número (float); inválidos viram NaN.
    """
    return pd.to_numeric(series, errors="coerce")


def user_id_to_customer_id(series: pd.Series) -> pd.Series:
    """
    Converte user_id numérico (ex: 10125) para customer_id do account (ex: C10125).
    """
    s = pd.to_numeric(series, errors="coerce").astype("Int64").astype(str)
    s = s.replace("<NA>", pd.NA)
    return "C" + s


def flag_gdpr_request(comments: pd.Series) -> pd.Series:
    """
    Cria flag simples para pedidos de exclusão/privacidade no suporte,
    baseado no campo comments.
    """
    txt = comments.fillna("").astype(str).str.lower()

    patterns = [
        "erase my data",
        "delete my data",
        "right to be forgotten",
        "gdpr",
        "forget me",
        "remove my data",
        "data deletion"
    ]

    mask = False
    for p in patterns:
        mask = mask | txt.str.contains(p, regex=False)

    return mask.astype(int)


def robust_engagement_bins(x: pd.Series) -> pd.Series:
    """
    Cria quartis (qcut) de forma robusta, evitando o erro:
    'Bin labels must be one fewer than the number of bin edges'

    Como:
    - qcut pode 'dropar' bins quando há muitos empates (duplicates='drop')
    - então o número de bins reais pode ser 2, 3 ou 4
    - eu ajusto os labels automaticamente para bater com os bins criados
    """
    x = pd.to_numeric(x, errors="coerce")

    # Se não tem dados suficientes ou não tem variação, retorno NA
    if x.notna().sum() < 4 or x.nunique(dropna=True) <= 1:
        return pd.Series([pd.NA] * len(x), index=x.index, dtype="object")

    # Primeiro cria bins sem labels (pra eu descobrir quantos bins foram possíveis)
    bins = pd.qcut(x, q=4, duplicates="drop")
    n_bins = bins.cat.categories.size

    labels_map = {
        2: ["low", "high"],
        3: ["low", "mid", "high"],
        4: ["low", "mid_low", "mid_high", "high"],
    }
    labels = labels_map.get(n_bins, [f"q{i+1}" for i in range(n_bins)])

    return pd.qcut(x, q=4, labels=labels, duplicates="drop")


# =========================
# 3) Leitura dos dados
# =========================

account_raw = pd.read_csv(ACCOUNT_PATH)
support_raw = pd.read_csv(SUPPORT_PATH)
activity_raw = pd.read_csv(ACTIVITY_PATH)

account = normalize_column_names(account_raw)
support = normalize_column_names(support_raw)
activity = normalize_column_names(activity_raw)

print("✅ Arquivos lidos!")
print("account cols:", list(account.columns))
print("support cols:", list(support.columns))
print("activity cols:", list(activity.columns))


# =========================
# 4) account_info: validação e limpeza
# =========================

# 4.1) customer_id
if "customer_id" not in account.columns:
    raise KeyError("account_info precisa ter a coluna 'customer_id'.")

account["customer_id"] = account["customer_id"].astype(str).str.strip()

# 4.2) email
if "email" in account.columns:
    account["email"] = account["email"].astype(str).str.strip()

# 4.3) state (do account é localização real)
if "state" in account.columns:
    account["state"] = account["state"].apply(clean_account_state)

# 4.4) plan
if "plan" in account.columns:
    account["plan"] = account["plan"].apply(clean_plan)

# 4.5) plan_list_price
if "plan_list_price" in account.columns:
    account["plan_list_price"] = numeric_coerce(account["plan_list_price"])
    account.loc[account["plan_list_price"] < 0, "plan_list_price"] = pd.NA

# 4.6) churn_status -> churn 0/1
if "churn_status" in account.columns:
    account["churn"] = account["churn_status"].apply(churn_status_to_int)
elif "churn" in account.columns:
    account["churn"] = account["churn"].apply(churn_status_to_int)
else:
    raise KeyError("Não encontrei 'churn_status' nem 'churn' no account_info.")

# 4.7) duplicados por customer_id (fico com o último)
account = account.drop_duplicates(subset=["customer_id"], keep="last")

print("\n✅ account_info limpo:")
print(account.head())


# =========================
# 5) customer_support: validação e limpeza
# =========================

if "user_id" not in support.columns:
    raise KeyError("customer_support precisa ter a coluna 'user_id'.")

support["customer_id"] = user_id_to_customer_id(support["user_id"])

if "ticket_time" in support.columns:
    support["ticket_time"] = safe_to_datetime(support["ticket_time"])

if "resolution_time_hours" in support.columns:
    support["resolution_time_hours"] = numeric_coerce(support["resolution_time_hours"])
    support.loc[support["resolution_time_hours"] < 0, "resolution_time_hours"] = pd.NA

    # cortar valores absurdos no p99 (pra não explodir gráfico)
    valid = support["resolution_time_hours"].dropna()
    if len(valid) >= 30:
        p99 = valid.quantile(0.99)
        support.loc[support["resolution_time_hours"] > p99, "resolution_time_hours"] = p99

if "channel" in support.columns:
    support["channel"] = support["channel"].astype(str).str.strip().str.lower()

if "topic" in support.columns:
    support["topic"] = support["topic"].astype(str).str.strip().str.lower()

# IMPORTANTE: 'state' no suporte é 0/1 (flag do ticket), não é estado dos EUA
if "state" in support.columns:
    support = support.rename(columns={"state": "ticket_state_flag"})

# flag GDPR
if "comments" in support.columns:
    support["gdpr_request_flag"] = flag_gdpr_request(support["comments"])
else:
    support["gdpr_request_flag"] = 0

print("\n✅ customer_support limpo:")
print(support.head())


# =========================
# 6) user_activity: validação e limpeza
# =========================

if "user_id" not in activity.columns:
    raise KeyError("user_activity precisa ter a coluna 'user_id'.")

activity["customer_id"] = user_id_to_customer_id(activity["user_id"])

if "event_time" in activity.columns:
    activity["event_time"] = safe_to_datetime(activity["event_time"])

if "event_type" in activity.columns:
    activity["event_type"] = activity["event_type"].astype(str).str.strip().str.lower()

print("\n✅ user_activity limpo:")
print(activity.head())


# =========================
# 7) Métricas de engajamento (activity_summary)
# =========================

max_event_time = activity["event_time"].max()
cutoff_30d = (max_event_time - pd.Timedelta(days=30)) if pd.notna(max_event_time) else pd.NaT

if activity.empty or "event_time" not in activity.columns:
    activity_summary = pd.DataFrame(columns=[
        "customer_id", "total_events", "active_days", "last_activity",
        "unique_event_types", "events_per_active_day",
        "events_last_30d", "active_days_last_30d"
    ])
else:
    base = activity.dropna(subset=["event_time"]).copy()

    activity_summary = (
        base.groupby("customer_id", as_index=False)
        .agg(
            total_events=("event_type", "count"),
            active_days=("event_time", lambda x: x.dt.date.nunique()),
            last_activity=("event_time", "max"),
            unique_event_types=("event_type", "nunique"),
        )
    )

    activity_summary["events_per_active_day"] = np.where(
        activity_summary["active_days"] > 0,
        activity_summary["total_events"] / activity_summary["active_days"],
        0
    )

    # últimos 30 dias
    if pd.notna(cutoff_30d):
        last30 = base[base["event_time"] >= cutoff_30d]
        last30_summary = (
            last30.groupby("customer_id", as_index=False)
            .agg(
                events_last_30d=("event_type", "count"),
                active_days_last_30d=("event_time", lambda x: x.dt.date.nunique())
            )
        )
        activity_summary = activity_summary.merge(last30_summary, on="customer_id", how="left")
    else:
        activity_summary["events_last_30d"] = pd.NA
        activity_summary["active_days_last_30d"] = pd.NA

    activity_summary[["events_last_30d", "active_days_last_30d"]] = (
        activity_summary[["events_last_30d", "active_days_last_30d"]].fillna(0)
    )

print("\n📊 activity_summary:")
print(activity_summary.head())


# =========================
# 8) Métricas de suporte (support_summary)
# =========================

max_ticket_time = support["ticket_time"].max() if "ticket_time" in support.columns else pd.NaT
cutoff_30d_tickets = (max_ticket_time - pd.Timedelta(days=30)) if pd.notna(max_ticket_time) else pd.NaT

def most_common(series: pd.Series):
    s = series.dropna()
    return s.value_counts().idxmax() if not s.empty else None

if support.empty:
    support_summary = pd.DataFrame(columns=[
        "customer_id", "total_tickets", "avg_resolution_time_hours", "max_resolution_time_hours",
        "unique_topics", "most_common_channel", "had_support",
        "tickets_last_30d", "gdpr_tickets"
    ])
else:
    support_summary = (
        support.groupby("customer_id", as_index=False)
        .agg(
            total_tickets=("topic", "count"),
            avg_resolution_time_hours=("resolution_time_hours", "mean"),
            max_resolution_time_hours=("resolution_time_hours", "max"),
            unique_topics=("topic", "nunique"),
            most_common_channel=("channel", most_common),
            gdpr_tickets=("gdpr_request_flag", "sum"),
        )
    )
    support_summary["had_support"] = support_summary["total_tickets"] > 0

    # últimos 30 dias
    if "ticket_time" in support.columns and pd.notna(cutoff_30d_tickets):
        last30 = support[support["ticket_time"] >= cutoff_30d_tickets]
        last30_summary = (
            last30.groupby("customer_id", as_index=False)
            .agg(tickets_last_30d=("topic", "count"))
        )
        support_summary = support_summary.merge(last30_summary, on="customer_id", how="left")
        support_summary["tickets_last_30d"] = support_summary["tickets_last_30d"].fillna(0)
    else:
        support_summary["tickets_last_30d"] = pd.NA

print("\n🎧 support_summary:")
print(support_summary.head())


# =========================
# 9) Montar data mart final (dashboard)
# =========================

dashboard = account.merge(activity_summary, on="customer_id", how="left")
dashboard = dashboard.merge(support_summary, on="customer_id", how="left")

# preencher métricas com 0 onde faz sentido
zero_cols = [
    "total_events", "active_days", "unique_event_types", "events_per_active_day",
    "events_last_30d", "active_days_last_30d",
    "total_tickets", "unique_topics", "tickets_last_30d", "gdpr_tickets"
]
for c in zero_cols:
    if c in dashboard.columns:
        dashboard[c] = dashboard[c].fillna(0)

# had_support: corrige warning futuro + garante bool de verdade
if "had_support" in dashboard.columns:
    dashboard["had_support"] = (
        dashboard["had_support"]
        .astype("boolean")   # dtype boolean do pandas (aceita NA)
        .fillna(False)
        .astype(bool)
    )

# dias desde última atividade (usando max_event_time como referência)
if "last_activity" in dashboard.columns and pd.notna(max_event_time):
    dashboard["days_since_last_activity"] = (max_event_time - dashboard["last_activity"]).dt.days
else:
    dashboard["days_since_last_activity"] = pd.NA

# quartis de engajamento (ROBUSTO, sem quebrar)
if "total_events" in dashboard.columns:
    dashboard["engagement_quartile"] = robust_engagement_bins(dashboard["total_events"])
else:
    dashboard["engagement_quartile"] = pd.NA

# KPI rápido: churn rate geral
churn_rate = dashboard["churn"].mean(skipna=True)
print(f"\n📌 Churn rate geral: {churn_rate:.3f} ({churn_rate*100:.1f}%)")

print("\n✅ Dashboard mart pronto (primeiras linhas):")
print(dashboard.head())


# =========================
# 10) Exportar
# =========================

account.to_csv(OUT_ACCOUNT_CLEAN, index=False)
support.to_csv(OUT_SUPPORT_CLEAN, index=False)
activity.to_csv(OUT_ACTIVITY_CLEAN, index=False)
dashboard.to_csv(OUT_DASHBOARD_MART, index=False)

print("\n📦 Arquivos exportados:")
print(f"- {OUT_ACCOUNT_CLEAN}")
print(f"- {OUT_SUPPORT_CLEAN}")
print(f"- {OUT_ACTIVITY_CLEAN}")
print(f"- {OUT_DASHBOARD_MART}")

"""
Próximos passos (dashboard):
- KPIs: churn rate, ARPU, % com suporte, churn por plano
- Visuais:
  1) Distribuição de planos (variável única)
  2) Distribuição de tickets (variável única)
  3) Churn por plano (multivariado)
  4) Churn por engajamento (quartil) (multivariado)
  5) Churn vs had_support (multivariado)
  6) Resolução média vs churn (multivariado)
  7) Segmento de risco: (baixo engajamento + muitos tickets) vs churn
"""