import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os

def run_exploration():
    # Settings
    plt.style.use('ggplot')
    sns.set_palette('viridis')
    
    base_path = Path(__file__).parent.parent
    figures_path = base_path / "notebooks" / "figures"
    figures_path.mkdir(parents=True, exist_ok=True)
    
    data_path = base_path / "data" / "master_dataset.csv"
    trades_path = base_path / "data" / "trades" / "energy_trades.csv"
    
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Section 2 — Energy Supply
    fig, axes = plt.subplots(3, 1, figsize=(15, 18), sharex=False)
    axes[0].plot(df.index, df['net_solar_kw'], color='orange', label='Solar', alpha=0.7)
    axes[0].plot(df.index, df['net_wind_kw'], color='blue', label='Wind', alpha=0.7)
    axes[0].plot(df.index, df['grid_available_kw'], color='green', label='Grid', alpha=0.5)
    axes[0].plot(df.index, df['total_supply_kw'], color='black', linestyle='--', label='Total Supply', alpha=0.8)
    axes[0].set_title('Energy Supply Sources (Full 2 Years)')
    axes[0].legend()

    summer_week = df.loc['2022-07-04':'2022-07-10']
    summer_week[['net_solar_kw', 'net_wind_kw', 'grid_available_kw']].plot(ax=axes[1], title='Summer Week (July 2022)')
    
    monthly_supply = df[['net_solar_kw', 'net_wind_kw', 'grid_available_kw']].resample('M').mean()
    monthly_supply.index = monthly_supply.index.strftime('%b %Y')
    monthly_supply.plot(kind='bar', ax=axes[2], stacked=False)
    axes[2].set_title('Average Monthly Supply by Source')
    axes[2].set_xticklabels(monthly_supply.index, rotation=45)
    plt.tight_layout()
    plt.savefig(figures_path / 'energy_supply.png')
    plt.close()

    # Section 3 — Hospital Demand
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    df['total_hospital_kw'].plot(ax=axes[0,0], title='Total Hospital Demand (Full 2 Years)', color='darkred')
    df.groupby(df.index.hour)['total_hospital_kw'].mean().plot(ax=axes[0,1], title='Average Demand by Hour of Day', marker='o')
    df.groupby(df.index.month)['total_hospital_kw'].mean().plot(kind='bar', ax=axes[1,0], title='Average Demand by Month')
    df['day_name'] = df.index.day_name()
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = df.pivot_table(index=df.index.hour, columns='day_name', values='total_hospital_kw', aggfunc='mean')[days_order]
    sns.heatmap(heatmap_data, ax=axes[1,1], cmap='YlOrRd', annot=False)
    axes[1,1].set_title('Mean Demand Heatmap (Hour vs Day)')
    plt.tight_layout()
    plt.savefig(figures_path / 'hospital_demand.png')
    plt.close()

    # Section 4 — Energy Balance
    fig = plt.figure(figsize=(15, 15))
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(df.index, df['energy_balance_kw'], color='gray', alpha=0.3)
    ax1.fill_between(df.index, df['energy_balance_kw'], 0, where=(df['energy_balance_kw'] > 0), color='green', alpha=0.4, label='Surplus')
    ax1.fill_between(df.index, df['energy_balance_kw'], 0, where=(df['energy_balance_kw'] < 0), color='red', alpha=0.4, label='Deficit')
    ax1.axhline(0, color='black', linestyle='--')
    ax1.set_title('Energy Balance Timeline')
    ax1.legend()
    ax2 = plt.subplot(2, 2, 3)
    sns.histplot(df['energy_balance_kw'], kde=True, ax=ax2, color='purple')
    ax3 = plt.subplot(2, 2, 4)
    df['balance_status'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax3)
    plt.tight_layout()
    plt.savefig(figures_path / 'energy_balance.png')
    plt.close()

    # Section 5 — Battery SoC
    bat_cols = [c for c in df.columns if c.startswith('bat_') and c.endswith('_pct')]
    fig, axes = plt.subplots(2, 1, figsize=(15, 14))
    df[bat_cols].plot(ax=axes[0], alpha=0.6)
    outage_starts = df[df['is_outage'] == 1].index
    for start in outage_starts[::20]: # Thinning for plot performance
        axes[0].axvline(start, color='red', alpha=0.05)
    df['outage_group'] = (df['is_outage'] != df['is_outage'].shift()).cumsum()
    outages = df[df['is_outage'] == 1].groupby('outage_group')
    longest_group = outages.size().idxmax()
    longest_outage_df = df[df['outage_group'] == longest_group]
    zoom_start = longest_outage_df.index.min() - pd.Timedelta(hours=4)
    zoom_end = longest_outage_df.index.max() + pd.Timedelta(hours=8)
    df.loc[zoom_start:zoom_end, bat_cols].plot(ax=axes[1])
    axes[1].axvspan(longest_outage_df.index.min(), longest_outage_df.index.max(), color='red', alpha=0.2)
    plt.tight_layout()
    plt.savefig(figures_path / 'battery_soc.png')
    plt.close()

    # Section 6 — Alerts
    fig, axes = plt.subplots(2, 1, figsize=(15, 12))
    color_map = {'NORMAL': 'green', 'WARNING': 'orange', 'CRITICAL': 'red'}
    for level, color in color_map.items():
        mask = df['alert_level'] == level
        axes[0].scatter(df.index[mask], [1]*mask.sum(), color=color, label=level, marker='|', alpha=0.5)
    df['alert_level'].value_counts().plot(kind='bar', ax=axes[1], color=['green', 'orange', 'red'])
    plt.tight_layout()
    plt.savefig(figures_path / 'alerts.png')
    plt.close()

    # Section 7 — Correlations
    plt.figure(figsize=(16, 12))
    numeric_df = df.select_dtypes(include=[np.number])
    corr = numeric_df.corr()
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdBu_r', center=0)
    plt.tight_layout()
    plt.savefig(figures_path / 'correlations.png')
    plt.close()

    # Section 8 — Renewables
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    df['renewable_fraction'].plot(ax=axes[0,0], title='Renewable Fraction Timeline', alpha=0.4)
    df.groupby(df.index.month)['renewable_fraction'].mean().plot(kind='bar', ax=axes[0,1])
    sns.scatterplot(data=df, x='net_solar_kw', y='net_wind_kw', hue='season', ax=axes[1,0], alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'renewables.png')
    plt.close()

    # Section 9 — Trades
    if trades_path.exists():
        trades = pd.read_csv(trades_path)
        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        fig, axes = plt.subplots(3, 1, figsize=(15, 18))
        axes[0].scatter(trades['timestamp'], [1]*len(trades), color='blue', marker='x')
        trades.groupby('donor_section')['traded_kw'].sum().plot(kind='bar', ax=axes[1])
        trades.groupby('receiver_section')['traded_kw'].sum().plot(kind='bar', ax=axes[2])
        plt.tight_layout()
        plt.savefig(figures_path / 'trades.png')
        plt.close()

    print(f"All figures generated in {figures_path}")

if __name__ == "__main__":
    run_exploration()
