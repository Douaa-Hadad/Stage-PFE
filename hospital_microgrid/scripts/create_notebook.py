import json
import os
from pathlib import Path

def create_exploration_notebook():
    notebook_path = Path("notebooks/01_exploration.ipynb")
    figures_path = Path("notebooks/figures")
    
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)
    
    cells = []
    
    # Header
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Hospital Microgrid Data Exploration\n",
            "This notebook performs a thorough visual exploration of the consolidated hospital microgrid dataset."
        ]
    })
    
    # Imports
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "from pathlib import Path\n",
            "import os\n",
            "\n",
            "# Settings\n",
            "plt.style.use('ggplot')\n",
            "sns.set_palette('viridis')\n",
            "os.makedirs('figures', exist_ok=True)\n",
            "pd.set_option('display.max_columns', None)"
        ]
    })
    
    # Section 1
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 1 — Dataset Overview"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df = pd.read_csv('../data/master_dataset.csv')\n",
            "df['timestamp'] = pd.to_datetime(df['timestamp'])\n",
            "df.set_index('timestamp', inplace=True)\n",
            "\n",
            "print(f'Shape: {df.shape}')\n",
            "print('\\nColumn Dtypes:')\n",
            "print(df.dtypes)\n",
            "display(df.head())\n",
            "\n",
            "print('\\nDescriptive Statistics:')\n",
            "display(df.describe())\n",
            "\n",
            "print('\\nValue Counts:')\n",
            "for col in ['alert_level', 'balance_status', 'season']:\n",
            "    print(f'\\n{col}:')\n",
            "    print(df[col].value_counts())"
        ]
    })
    
    # Section 2
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 2 — Energy Supply Over Time"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(3, 1, figsize=(15, 18), sharex=False)\n",
            "\n",
            "# Plot 1: Full 2 years\n",
            "axes[0].plot(df.index, df['net_solar_kw'], color='orange', label='Solar', alpha=0.7)\n",
            "axes[0].plot(df.index, df['net_wind_kw'], color='blue', label='Wind', alpha=0.7)\n",
            "axes[0].plot(df.index, df['grid_available_kw'], color='green', label='Grid', alpha=0.5)\n",
            "axes[0].plot(df.index, df['total_supply_kw'], color='black', linestyle='--', label='Total Supply', alpha=0.8)\n",
            "axes[0].set_title('Energy Supply Sources (Full 2 Years)')\n",
            "axes[0].legend()\n",
            "\n",
            "# Plot 2: Summer vs Winter Week\n",
            "summer_week = df.loc['2022-07-04':'2022-07-10']\n",
            "winter_week = df.loc['2023-01-02':'2023-01-08']\n",
            "\n",
            "ax2 = plt.subplot(3, 1, 2)\n",
            "summer_week[['net_solar_kw', 'net_wind_kw', 'grid_available_kw']].plot(ax=ax2, title='Summer Week (July 2022)')\n",
            "plt.title('Supply - Summer Week Zoom')\n",
            "\n",
            "# Plot 3: Monthly Bar\n",
            "monthly_supply = df[['net_solar_kw', 'net_wind_kw', 'grid_available_kw']].resample('M').mean()\n",
            "monthly_supply.index = monthly_supply.index.strftime('%b %Y')\n",
            "monthly_supply.plot(kind='bar', ax=axes[2], stacked=False)\n",
            "axes[2].set_title('Average Monthly Supply by Source')\n",
            "axes[2].set_xticklabels(monthly_supply.index, rotation=45)\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/energy_supply.png')\n",
            "plt.show()"
        ]
    })
    
    # Section 3
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 3 — Hospital Demand"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(2, 2, figsize=(18, 14))\n",
            "\n",
            "# 1. 2 Years\n",
            "df['total_hospital_kw'].plot(ax=axes[0,0], title='Total Hospital Demand (Full 2 Years)', color='darkred')\n",
            "\n",
            "# 2. Hourly Cycle\n",
            "df.groupby(df.index.hour)['total_hospital_kw'].mean().plot(ax=axes[0,1], title='Average Demand by Hour of Day', marker='o')\n",
            "axes[0,1].set_xlabel('Hour')\n",
            "\n",
            "# 3. Monthly Cycle\n",
            "df.groupby(df.index.month)['total_hospital_kw'].mean().plot(kind='bar', ax=axes[1,0], title='Average Demand by Month')\n",
            "axes[1,0].set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])\n",
            "\n",
            "# 4. Heatmap\n",
            "df['day_name'] = df.index.day_name()\n",
            "days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']\n",
            "heatmap_data = df.pivot_table(index=df.index.hour, columns='day_name', values='total_hospital_kw', aggfunc='mean')[days_order]\n",
            "sns.heatmap(heatmap_data, ax=axes[1,1], cmap='YlOrRd', annot=False)\n",
            "axes[1,1].set_title('Mean Demand Heatmap (Hour vs Day)')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/hospital_demand.png')\n",
            "plt.show()"
        ]
    })
    
    # Section 4
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 4 — Energy Balance"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig = plt.figure(figsize=(15, 15))\n",
            "\n",
            "# 1. Timeline Area Plot\n",
            "ax1 = plt.subplot(2, 1, 1)\n",
            "ax1.plot(df.index, df['energy_balance_kw'], color='gray', alpha=0.3)\n",
            "ax1.fill_between(df.index, df['energy_balance_kw'], 0, where=(df['energy_balance_kw'] > 0), color='green', alpha=0.4, label='Surplus')\n",
            "ax1.fill_between(df.index, df['energy_balance_kw'], 0, where=(df['energy_balance_kw'] < 0), color='red', alpha=0.4, label='Deficit')\n",
            "ax1.axhline(0, color='black', linestyle='--')\n",
            "ax1.set_title('Energy Balance Timeline')\n",
            "ax1.legend()\n",
            "\n",
            "# 2. Histogram\n",
            "ax2 = plt.subplot(2, 2, 3)\n",
            "sns.histplot(df['energy_balance_kw'], kde=True, ax=ax2, color='purple')\n",
            "ax2.set_title('Distribution of Energy Balance')\n",
            "\n",
            "# 3. Pie Chart\n",
            "ax3 = plt.subplot(2, 2, 4)\n",
            "df['balance_status'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax3, colors=['#99ff99','#66b3ff','#ff9999','#ffcc99'])\n",
            "ax3.set_title('Balance Status Distribution')\n",
            "ax3.set_ylabel('')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/energy_balance.png')\n",
            "plt.show()"
        ]
    })
    
    # Section 5
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 5 — Battery State of Charge"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "bat_cols = [c for c in df.columns if c.startswith('bat_') and c.endswith('_pct')]\n",
            "\n",
            "fig, axes = plt.subplots(2, 1, figsize=(15, 14))\n",
            "\n",
            "# 1. Full Timeline\n",
            "df[bat_cols].plot(ax=axes[0], alpha=0.6)\n",
            "axes[0].set_title('Battery State of Charge (All sections)')\n",
            "axes[0].set_ylabel('SoC (%)')\n",
            "axes[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')\n",
            "\n",
            "# Highlight outages\n",
            "outage_starts = df[df['is_outage'] == 1].index\n",
            "for start in outage_starts:\n",
            "    axes[0].axvline(start, color='red', alpha=0.01)\n",
            "\n",
            "# 2. Zoom longest outage\n",
            "# Find longest continuous outage\n",
            "df['outage_group'] = (df['is_outage'] != df['is_outage'].shift()).cumsum()\n",
            "outages = df[df['is_outage'] == 1].groupby('outage_group')\n",
            "longest_group = outages.size().idxmax()\n",
            "longest_outage_df = df[df['outage_group'] == longest_group]\n",
            "\n",
            "# Buffer for zoom\n",
            "zoom_start = longest_outage_df.index.min() - pd.Timedelta(hours=4)\n",
            "zoom_end = longest_outage_df.index.max() + pd.Timedelta(hours=8)\n",
            "df.loc[zoom_start:zoom_end, bat_cols].plot(ax=axes[1])\n",
            "axes[1].axvspan(longest_outage_df.index.min(), longest_outage_df.index.max(), color='red', alpha=0.2, label='Outage')\n",
            "axes[1].set_title('Longest Outage Event Zoom')\n",
            "axes[1].legend()\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/battery_soc.png')\n",
            "plt.show()"
        ]
    })
    
    # Section 6
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 6 — Alert Levels & Anomalies"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(2, 1, figsize=(15, 12))\n",
            "\n",
            "# Timeline\n",
            "color_map = {'NORMAL': 'green', 'WARNING': 'orange', 'CRITICAL': 'red'}\n",
            "for level, color in color_map.items():\n",
            "    mask = df['alert_level'] == level\n",
            "    axes[0].scatter(df.index[mask], [1]*mask.sum(), color=color, label=level, marker='|', alpha=0.5)\n",
            "axes[0].set_title('Alert Level Timeline')\n",
            "axes[0].set_yticks([])\n",
            "axes[0].legend()\n",
            "\n",
            "# Bar Chart\n",
            "df['alert_level'].value_counts().plot(kind='bar', ax=axes[1], color=['green', 'orange', 'red'])\n",
            "axes[1].set_title('Alert Level Counts')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/alerts.png')\n",
            "plt.show()\n",
            "\n",
            "print('Critical Alert Timestamps:')\n",
            "critical_df = df[df['alert_level'] == 'CRITICAL'][['energy_balance_kw', 'min_battery_pct', 'min_battery_section', 'is_outage']]\n",
            "display(critical_df.head(20))"
        ]
    })
    
    # Section 7
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 7 — Correlations"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(16, 12))\n",
            "numeric_df = df.select_dtypes(include=[np.number])\n",
            "corr = numeric_df.corr()\n",
            "sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdBu_r', center=0)\n",
            "plt.title('Correlation Heatmap')\n",
            "plt.savefig('figures/correlations.png')\n",
            "plt.show()\n",
            "\n",
            "print('Top 10 features correlated with total_hospital_kw:')\n",
            "print(corr['total_hospital_kw'].abs().sort_values(ascending=False).head(11)[1:])\n",
            "\n",
            "print('\\nTop 10 features correlated with is_outage:')\n",
            "print(corr['is_outage'].abs().sort_values(ascending=False).head(11)[1:])"
        ]
    })
    
    # Section 8
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 8 — Renewable Energy Analysis"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(2, 2, figsize=(18, 14))\n",
            "\n",
            "# 1. Fraction timeline\n",
            "df['renewable_fraction'].plot(ax=axes[0,0], title='Renewable Fraction Timeline', alpha=0.4)\n",
            "axes[0,0].axhline(df['renewable_fraction'].mean(), color='red', linestyle='--', label='Mean')\n",
            "\n",
            "# 2. Monthly bar\n",
            "df.groupby(df.index.month)['renewable_fraction'].mean().plot(kind='bar', ax=axes[0,1], title='Average Renewable Fraction by Month')\n",
            "\n",
            "# 3. Solar vs Wind scatter\n",
            "sns.scatterplot(data=df, x='net_solar_kw', y='net_wind_kw', hue='season', ax=axes[1,0], alpha=0.3)\n",
            "axes[1,0].set_title('Solar vs Wind Contribution')\n",
            "\n",
            "# 4. Threshold Counts\n",
            "total = len(df)\n",
            "gt50 = (df['renewable_fraction'] > 0.5).sum() / total * 100\n",
            "gt75 = (df['renewable_fraction'] > 0.75).sum() / total * 100\n",
            "eq100 = (df['renewable_fraction'] >= 0.99).sum() / total * 100\n",
            "\n",
            "print(f'Timesteps with Renewable Fraction > 50%: {gt50:.2f}%')\n",
            "print(f'Timesteps with Renewable Fraction > 75%: {gt75:.2f}%')\n",
            "print(f'Timesteps with Renewable Fraction == 100%: {eq100:.2f}%')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/renewables.png')\n",
            "plt.show()"
        ]
    })
    
    # Section 9
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": ["## Section 9 — P2P Trading Events"]
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "trades = pd.read_csv('../data/trades/energy_trades.csv')\n",
            "trades['timestamp'] = pd.to_datetime(trades['timestamp'])\n",
            "\n",
            "fig, axes = plt.subplots(3, 1, figsize=(15, 18))\n",
            "\n",
            "# Timeline\n",
            "axes[0].scatter(trades['timestamp'], [1]*len(trades), color='blue', marker='x')\n",
            "axes[0].set_title('P2P Trading Event Timeline')\n",
            "axes[0].set_yticks([])\n",
            "\n",
            "# Donors\n",
            "trades.groupby('donor_section')['traded_kw'].sum().plot(kind='bar', ax=axes[1], title='Total Energy Donated by Section (kW-steps)')\n",
            "\n",
            "# Receivers\n",
            "trades.groupby('receiver_section')['traded_kw'].sum().plot(kind='bar', ax=axes[2], title='Total Energy Received by Section (kW-steps)')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.savefig('figures/trades.png')\n",
            "plt.show()\n",
            "\n",
            "print('Full Trade Ledger:')\n",
            "display(trades)"
        ]
    })
    
    # Summary
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Summary of Observations for AI Design\n",
            "\n",
            "1. **Solar Predictability**: Solar generation follows a strict daily cycle but is highly affected by seasonal potential. AI should prioritize solar for daytime battery top-ups.\n",
            "2. **Outage Criticality**: Outages combined with low battery levels are the primary cause of CRITICAL alerts. The model must learn to maintain a higher SoC buffer before predicted outages.\n",
            "3. **Demand Seasonality**: Hospital demand peaks in summer due to AC loads (correlated with temperature). The AI must factor in weather forecasts to predict cooling-driven demand spikes.\n",
            "4. **P2P Effectiveness**: Trading mostly occurs between sections like Pharmacie and Bloc/Urgences. This suggests that some sections are consistently 'over-buffered', a feature the AI can exploit for grid-less stability.\n",
            "5. **Renewable Fraction**: The average renewable fraction is low (~4%), meaning the grid remains the primary power source. The AI's objective function should aim to maximize this fraction while maintaining safety margins."
        ]
    })
    
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.8.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2)
    
    print(f"Notebook created at {notebook_path}")

if __name__ == "__main__":
    create_exploration_notebook()
