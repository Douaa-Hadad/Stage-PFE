import json
import os
from pathlib import Path

def create_generator_notebook():
    notebook_path = Path("notebooks/05_generators.ipynb")
    figures_path = Path("notebooks/figures")
    
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)
    
    cells = []
    
    # Cell 1
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Backup Diesel Generators & Resilience Analysis\n",
            "This notebook analyzes the performance, fuel depletion, temperature derating, maintenance windows, and resilience impact of the 4 diesel backup generators in the hospital microgrid system."
        ]
    })
    
    # Cell 2
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
    
    # Cell 3
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 1 — Generator Overview & Specifications\n",
            "Let's load the generator files and inspect their structure and specifications."
        ]
    })
    
    # Cell 4
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "generators = {}\n",
            "gen_ids = ['g1', 'g2', 'g3', 'g4']\n",
            "for g in gen_ids:\n",
            "    path = Path(f'../data/supply/generators/generator_{g}.csv')\n",
            "    if path.exists():\n",
            "        generators[g] = pd.read_csv(path)\n",
            "        generators[g]['timestamp'] = pd.to_datetime(generators[g]['timestamp'])\n",
            "        print(f\"Loaded Generator {g.upper()} - {len(generators[g])} rows.\")\n",
            "    else:\n",
            "        print(f\"Warning: Generator {g} data not found at {path}\")\n",
            "\n",
            "# Specs Table\n",
            "specs = pd.DataFrame([\n",
            "    {\"Generator\": \"G1\", \"Capacity (kW)\": 300, \"Fuel Tank (Hours)\": 48, \"Threshold (Steps)\": 1, \"Coverage\": \"P1 (Rea, Bloc, Urg, Neo)\"},\n",
            "    {\"Generator\": \"G2\", \"Capacity (kW)\": 200, \"Fuel Tank (Hours)\": 36, \"Threshold (Steps)\": 1, \"Coverage\": \"P2 (Dial, Mat, Lab, Phar)\"},\n",
            "    {\"Generator\": \"G3\", \"Capacity (kW)\": 150, \"Fuel Tank (Hours)\": 24, \"Threshold (Steps)\": 5, \"Coverage\": \"P3 (Radio, Med Int)\"},\n",
            "    {\"Generator\": \"G4\", \"Capacity (kW)\": 100, \"Fuel Tank (Hours)\": 12, \"Threshold (Steps)\": 5, \"Coverage\": \"P4-P5 (Consult, Admin, Gen)\"},\n",
            "])\n",
            "display(specs)"
        ]
    })
    
    # Cell 5
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 2 — Runtime Analysis\n",
            "Let's see how long each generator ran during the 2-year simulation."
        ]
    })
    
    # Cell 6
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "runtimes = []\n",
            "for g in gen_ids:\n",
            "    if g in generators:\n",
            "        runtime_h = generators[g]['is_running'].sum() * 0.5\n",
            "        runtimes.append(runtime_h)\n",
            "    else:\n",
            "        runtimes.append(0.0)\n",
            "\n",
            "plt.figure(figsize=(10, 6))\n",
            "bars = plt.bar(['G1', 'G2', 'G3', 'G4'], runtimes, color=['#ef4444', '#f97316', '#eab308', '#94a3b8'])\n",
            "plt.title('Total Generator Runtime Hours (2 Years)')\n",
            "plt.ylabel('Hours')\n",
            "plt.xlabel('Generator')\n",
            "for bar in bars:\n",
            "    yval = bar.get_height()\n",
            "    plt.text(bar.get_x() + bar.get_width()/2, yval + 1, f\"{yval:.1f}h\", ha='center', va='bottom', fontweight='bold')\n",
            "plt.savefig('figures/generator_runtime.png')\n",
            "plt.show()"
        ]
    })
    
    # Cell 7
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 3 — Fuel Consumption & Depletion Over Time\n",
            "Let's visualize the fuel levels of the generators over time. Since we have a 2-year timeline, let's zoom in on a period with outages to see fuel depletion and subsequent recharging."
        ]
    })
    
    # Cell 8
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(15, 7))\n",
            "if 'g1' in generators:\n",
            "    g1_run_idx = generators['g1'][generators['g1']['is_running'] == 1].index\n",
            "    if len(g1_run_idx) > 0:\n",
            "        start_idx = max(0, g1_run_idx[0] - 10)\n",
            "        end_idx = min(len(generators['g1']), g1_run_idx[0] + 50)\n",
            "        \n",
            "        for g in gen_ids:\n",
            "            if g in generators:\n",
            "                sub_df = generators[g].iloc[start_idx:end_idx]\n",
            "                plt.plot(sub_df['timestamp'], sub_df['fuel_level_pct'], label=f\"{g.upper()} Fuel %\")\n",
            "        \n",
            "        plt.title('Generator Fuel Level Depletion and Refill (Zoomed Outage Window)')\n",
            "        plt.ylabel('Fuel Level (%)')\n",
            "        plt.xlabel('Timestamp')\n",
            "        plt.legend()\n",
            "        plt.savefig('figures/generator_fuel_zoom.png')\n",
            "        plt.show()"
        ]
    })
    
    # Cell 9
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 4 — Temperature Derating\n",
            "Generator capacity decreases at very high temperatures. Let's see how temperature derating behaves relative to the ambient temperature."
        ]
    })
    
    # Cell 10
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "weather_path = Path('../data/weather/meteo_casablanca.csv')\n",
            "if weather_path.exists() and 'g1' in generators:\n",
            "    weather = pd.read_csv(weather_path)\n",
            "    merged = generators['g1'].merge(weather[['timestamp', 'temperature_2m']], on='timestamp', how='left')\n",
            "    \n",
            "    plt.figure(figsize=(10, 6))\n",
            "    plt.scatter(merged['temperature_2m'], merged['temp_derating_factor'], alpha=0.5, color='purple')\n",
            "    plt.title('Generator Derating Factor vs Temperature')\n",
            "    plt.xlabel('Temperature (°C)')\n",
            "    plt.ylabel('Capacity Derating Factor')\n",
            "    plt.grid(True)\n",
            "    plt.savefig('figures/generator_derating.png')\n",
            "    plt.show()"
        ]
    })
    
    # Cell 11
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 5 — Planned Maintenance\n",
            "Let's see when planned maintenance windows occurred."
        ]
    })
    
    # Cell 12
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(12, 4))\n",
            "for idx, g in enumerate(gen_ids):\n",
            "    if g in generators:\n",
            "        maint_times = generators[g][generators[g]['is_maintenance'] == 1]['timestamp']\n",
            "        if len(maint_times) > 0:\n",
            "            plt.scatter(maint_times, [idx + 1] * len(maint_times), label=f\"{g.upper()} Maint\", marker='|', s=200)\n",
            "\n",
            "plt.yticks(range(1, 5), ['G1', 'G2', 'G3', 'G4'])\n",
            "plt.title('Planned Maintenance Timeline')\n",
            "plt.xlabel('Timestamp')\n",
            "plt.ylim(0.5, 4.5)\n",
            "plt.grid(True)\n",
            "plt.savefig('figures/generator_maintenance.png')\n",
            "plt.show()"
        ]
    })
    
    # Cell 13
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 6 — Activation Events Analysis\n",
            "Let's count the number of activations for each generator and average duration."
        ]
    })
    
    # Cell 14
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "activation_stats = []\n",
            "for g in gen_ids:\n",
            "    if g in generators:\n",
            "        df_g = generators[g]\n",
            "        starts = (df_g['is_running'] == 1) & (df_g['is_running'].shift(1) == 0)\n",
            "        num_starts = starts.sum()\n",
            "        total_runs = df_g['is_running'].sum()\n",
            "        avg_duration = (total_runs * 0.5) / num_starts if num_starts > 0 else 0.0\n",
            "        activation_stats.append({\n",
            "            \"Generator\": g.upper(),\n",
            "            \"Activations\": num_starts,\n",
            "            \"Avg Duration (Hours)\": round(avg_duration, 2),\n",
            "            \"Max Output (kW)\": df_g['output_kw'].max()\n",
            "        })\n",
            "display(pd.DataFrame(activation_stats))"
        ]
    })
    
    # Cell 15
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 7 — Battery Recharge Impact\n",
            "Let's see how generators help recharge the critical battery banks during outages."
        ]
    })
    
    # Cell 16
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "bat_path = Path('../data/batteries/bat_reanimation.csv')\n",
            "if bat_path.exists() and 'g1' in generators:\n",
            "    bat_df = pd.read_csv(bat_path)\n",
            "    bat_df['timestamp'] = pd.to_datetime(bat_df['timestamp'])\n",
            "    merged = generators['g1'].merge(bat_df, on='timestamp', how='left')\n",
            "    \n",
            "    outage_mask = (merged['is_running'] == 1)\n",
            "    if outage_mask.sum() > 0:\n",
            "        run_idx = merged[outage_mask].index[0]\n",
            "        sub = merged.iloc[max(0, run_idx-10):min(len(merged), run_idx+30)]\n",
            "        \n",
            "        fig, ax1 = plt.subplots(figsize=(12, 6))\n",
            "        ax2 = ax1.twinx()\n",
            "        \n",
            "        ax1.plot(sub['timestamp'], sub['charge_pct'], 'g-', label='Battery SoC (%)')\n",
            "        ax2.plot(sub['timestamp'], sub['output_kw'], 'r--', label='G1 Output (kW)')\n",
            "        \n",
            "        ax1.set_xlabel('Timestamp')\n",
            "        ax1.set_ylabel('Battery SoC (%)', color='g')\n",
            "        ax2.set_ylabel('Generator Output (kW)', color='r')\n",
            "        plt.title('Critical Section (Reanimation) Battery Recharge during Outage')\n",
            "        plt.savefig('figures/battery_recharge_impact.png')\n",
            "        plt.show()"
        ]
    })
    
    # Cell 17
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 8 — Trade Scenario Analysis\n",
            "Let's look at the Peer-to-Peer (P2P) trading ledger and see how trade scenarios and cost savings are distributed."
        ]
    })
    
    # Cell 18
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "trades_path = Path('../data/trades/energy_trades.csv')\n",
            "if trades_path.exists():\n",
            "    trades = pd.read_csv(trades_path)\n",
            "    print(f\"Total trades logged: {len(trades)}\")\n",
            "    \n",
            "    fig, axes = plt.subplots(1, 2, figsize=(16, 7))\n",
            "    \n",
            "    if 'trade_scenario' in trades.columns:\n",
            "        trades['trade_scenario'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=axes[0])\n",
            "        axes[0].set_title('P2P Trade Scenario Distribution')\n",
            "        axes[0].set_ylabel('')\n",
            "        \n",
            "    if 'cost_saving_eur' in trades.columns:\n",
            "        trades.groupby('trade_scenario')['cost_saving_eur'].sum().plot(kind='bar', ax=axes[1], color='teal')\n",
            "        axes[1].set_title('Total Cost Savings by Scenario (EUR)')\n",
            "        axes[1].set_ylabel('Savings (€)')\n",
            "        axes[1].set_xlabel('Scenario')\n",
            "        plt.xticks(rotation=45, ha='right')\n",
            "        \n",
            "    plt.tight_layout()\n",
            "    plt.savefig('figures/trade_scenarios_savings.png')\n",
            "    plt.show()"
        ]
    })
    
    # Cell 19
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Section 9 — 3-Layer Resilience Summary\n",
            "Let's compute the overall contributions of our 3 resilience layers:\n",
            "- **Layer 1**: Renewables (Solar + Wind)\n",
            "- **Layer 2**: Generators (Diesel backup)\n",
            "- **Layer 3**: Battery P2P Trading"
        ]
    })
    
    # Cell 20
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "master_path = Path('../data/master_dataset.csv')\n",
            "if master_path.exists():\n",
            "    df_m = pd.read_csv(master_path)\n",
            "    \n",
            "    total_solar = df_m['net_solar_kw'].sum() * 0.5\n",
            "    total_wind = df_m['net_wind_kw'].sum() * 0.5\n",
            "    total_gen = df_m['total_generator_kw'].sum() * 0.5\n",
            "    \n",
            "    total_trade = 0.0\n",
            "    if trades_path.exists():\n",
            "        total_trade = trades['traded_kw'].sum() * 0.5\n",
            "        \n",
            "    print(\"Resilience Contribution Summary (kWh):\")\n",
            "    print(f\"  Layer 1 - Solar Generation:       {total_solar:,.2f} kWh\")\n",
            "    print(f\"  Layer 1 - Wind Generation:        {total_wind:,.2f} kWh\")\n",
            "    print(f\"  Layer 2 - Backup Diesel Gen:      {total_gen:,.2f} kWh\")\n",
            "    print(f\"  Layer 3 - P2P Battery Trades:     {total_trade:,.2f} kWh\")\n",
            "    \n",
            "    plt.figure(figsize=(10, 6))\n",
            "    categories = ['Solar', 'Wind', 'Generators', 'P2P Trades']\n",
            "    values = [total_solar, total_wind, total_gen, total_trade]\n",
            "    plt.bar(categories, values, color=['#ffc078', '#a5d8ff', '#ffa500', '#4dabf7'])\n",
            "    plt.title('Overall Resilience Energy Generation / Transfer (kWh)')\n",
            "    plt.ylabel('Energy (kWh)')\n",
            "    plt.savefig('figures/resilience_summary.png')\n",
            "    plt.show()"
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
    create_generator_notebook()
