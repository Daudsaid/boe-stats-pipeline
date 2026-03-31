# etl/transform.py

import pandas as pd
import os

RAW_DATA_PATH = "data/raw"
TRANSFORMED_DATA_PATH = "data/transformed"


def load_raw(series_name: str) -> pd.DataFrame:
    filepath = os.path.join(RAW_DATA_PATH, f"{series_name}.csv")
    df = pd.read_csv(filepath, parse_dates=["date"])
    return df


def transform_base_rate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"base_rate": "rate_pct"})
    df["rate_change"] = df["rate_pct"].diff()
    df["rate_direction"] = df["rate_change"].apply(
        lambda x: "hike" if x > 0 else ("cut" if x < 0 else "hold")
    )
    return df[["date", "rate_pct", "rate_change", "rate_direction", "series_code", "extracted_at"]]


def transform_exchange_rates(df_usd: pd.DataFrame, df_eur: pd.DataFrame) -> pd.DataFrame:
    df = df_usd.rename(columns={"gbp_usd": "gbp_usd"}).merge(
        df_eur.rename(columns={"gbp_eur": "gbp_eur"})[["date", "gbp_eur"]],
        on="date",
        how="inner"
    )
    df["usd_monthly_change_pct"] = df["gbp_usd"].pct_change() * 100
    df["eur_monthly_change_pct"] = df["gbp_eur"].pct_change() * 100
    return df[["date", "gbp_usd", "gbp_eur", "usd_monthly_change_pct", "eur_monthly_change_pct", "extracted_at"]]


def transform_mortgage_rate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"mortgage_rate": "rate_pct"})
    df["rate_change"] = df["rate_pct"].diff()
    df["spread_vs_base"] = None  # populated in dbt mart
    return df[["date", "rate_pct", "rate_change", "series_code", "extracted_at"]]


def transform_m4(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"m4_money_supply": "m4_gbp_millions"})
    df["m4_monthly_change"] = df["m4_gbp_millions"].diff()
    df["m4_growth_pct"] = df["m4_gbp_millions"].pct_change() * 100
    return df[["date", "m4_gbp_millions", "m4_monthly_change", "m4_growth_pct", "series_code", "extracted_at"]]


def save_transformed(df: pd.DataFrame, name: str):
    os.makedirs(TRANSFORMED_DATA_PATH, exist_ok=True)
    filepath = os.path.join(TRANSFORMED_DATA_PATH, f"{name}.csv")
    df.to_csv(filepath, index=False)
    print(f"[transform] Saved → {filepath}")


if __name__ == "__main__":
    base_rate = transform_base_rate(load_raw("base_rate"))
    save_transformed(base_rate, "base_rate")

    fx = transform_exchange_rates(load_raw("gbp_usd"), load_raw("gbp_eur"))
    save_transformed(fx, "exchange_rates")

    mortgage = transform_mortgage_rate(load_raw("mortgage_rate"))
    save_transformed(mortgage, "mortgage_rate")

    m4 = transform_m4(load_raw("m4_money_supply"))
    save_transformed(m4, "m4_money_supply")