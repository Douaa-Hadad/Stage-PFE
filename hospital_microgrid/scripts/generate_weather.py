import requests
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
LATITUDE  = 33.5731
LONGITUDE = -7.5898
START     = "2022-01-01"
END       = "2023-12-31"
OUTPUT    = Path(__file__).parent / "weather" / "meteo_casablanca.csv"

# ─────────────────────────────────────────────
#  FETCH FROM OPEN-METEO
# ─────────────────────────────────────────────
def fetch_weather() -> dict:
    print("Fetching weather data from Open-Meteo...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   LATITUDE,
        "longitude":  LONGITUDE,
        "start_date": START,
        "end_date":   END,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "shortwave_radiation",
            "direct_radiation",
            "diffuse_radiation",
            "windspeed_10m",
            "winddirection_10m",
            "windgusts_10m",
            "precipitation",
            "weathercode",
        ]),
        "timezone": "Africa/Casablanca",
    }
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    print("  Fetch successful.")
    return response.json()

# ─────────────────────────────────────────────
#  PROCESS INTO DATAFRAME
# ─────────────────────────────────────────────
def process(raw: dict) -> pd.DataFrame:
    df = pd.DataFrame(raw["hourly"])
    df.rename(columns={"time": "timestamp"}, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["weathercode"] = df["weathercode"].astype(float)
    df.set_index("timestamp", inplace=True)

    # upsample hourly to 30-minute via time interpolation
    df_30 = df.resample("30min").interpolate(method="time")
    df_30["weathercode"] = df_30["weathercode"].round().astype(int)

    # derived features
    df_30["hour"]        = df_30.index.hour + df_30.index.minute / 60
    df_30["day_of_week"] = df_30.index.dayofweek
    df_30["month"]       = df_30.index.month
    df_30["is_weekend"]  = (df_30.index.dayofweek >= 5).astype(int)
    df_30["is_daytime"]  = (df_30["shortwave_radiation"] > 0).astype(int)

    max_ghi = df_30["shortwave_radiation"].max()
    df_30["solar_potential"] = (df_30["shortwave_radiation"] / max_ghi).round(4)

    def wind_potential(speed_kmh: float) -> float:
        if speed_kmh < 10 or speed_kmh > 90: return 0.0
        elif speed_kmh <= 40: return round((speed_kmh - 10) / 30, 4)
        else: return 1.0

    df_30["wind_potential"] = df_30["windspeed_10m"].apply(wind_potential)

    # missing value handling
    df_30.interpolate(method="time", limit=4, inplace=True)
    df_30.ffill(inplace=True)
    df_30.bfill(inplace=True)

    float_cols = df_30.select_dtypes(include=[float]).columns
    df_30[float_cols] = df_30[float_cols].round(4)

    df_30["season"] = df_30["month"].map(lambda m:
        "winter" if m in [12, 1, 2] else
        "spring" if m in [3, 4, 5]  else
        "summer" if m in [6, 7, 8]  else "autumn")

    df_30.reset_index(inplace=True)
    return df_30

# ─────────────────────────────────────────────
#  VALIDATION
# ─────────────────────────────────────────────
def validate(df: pd.DataFrame):
    print("\nValidation report:")
    print(f"  Rows          : {len(df):,}")
    print(f"  Date range    : {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Columns ({len(df.columns)})  : {list(df.columns)}")
    print(f"  Nulls         : {df.isnull().sum().sum()}")
    print(f"  Temp range    : {df['temperature_2m'].min():.1f}°C to {df['temperature_2m'].max():.1f}°C")
    print(f"  Wind range    : {df['windspeed_10m'].min():.1f} to {df['windspeed_10m'].max():.1f} km/h")
    print(f"  Max GHI       : {df['shortwave_radiation'].max():.1f} W/m²")
    print(f"  Daytime rows  : {df['is_daytime'].sum():,} / {len(df):,}")
    print(f"  Wind active   : {(df['wind_potential'] > 0).sum():,} timesteps")
    expected = 2 * 365 * 48
    status = "OK" if abs(len(df) - expected) <= 96 else "WARNING"
    print(f"  Row count     : {status} (expected ~{expected:,}, got {len(df):,})")

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    raw = fetch_weather()
    df  = process(raw)
    validate(df)
    df.to_csv(OUTPUT, index=False)
    print(f"\nSaved to {OUTPUT}")
    print(f"File size: {OUTPUT.stat().st_size / 1024:.1f} KB")
