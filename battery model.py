import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Simulate ERCOT-like price data
np.random.seed(42)
hours = pd.date_range(start='2020-01-01', periods=24*7, freq='h')
df = pd.DataFrame(index=hours)
# real time energy price --- normal dis around $30 change if we can get data
df['rtm_price'] = np.random.normal(loc=30, scale=10, size=len(hours)).clip(min=0) # $/MWh  
# regulation reserve price (ancillary services) --- normal dis around $5 change if we can get data 
df['reg_price'] = np.random.normal(loc=5, scale=2, size=len(hours)).clip(min=0) # $/MWh 

# Battery specs
E_max = 100   # MWh
P_max = 50    # MW
soc = 50      # Initial state of charge
eta_ch = 0.95
eta_dis = 0.95
soc_min = 0.1 * E_max
soc_max = E_max
degradation_cost = 10  # $/MWh throughput

# Strategy thresholds
low_price = 20   # buy (charge) if price < $20
high_price = 40  # sell (discharge) if price > $40

# Run dispatch loop
charges, discharges, socs, as_regs = [], [], [], []

for i, row in df.iterrows():
    price = row['rtm_price']
    reg_price = row['reg_price']
    
    charge = discharge = as_reg = 0

    if price < low_price and soc < soc_max:
        charge = min(P_max, (soc_max - soc) / eta_ch)
        soc += charge * eta_ch
    elif price > high_price and soc > soc_min:
        discharge = min(P_max, (soc - soc_min) * eta_dis)
        soc -= discharge / eta_dis
    else:
        as_reg = 10  # Reserve 10 MW for ancillary services - how to add this?

    # Save state
    charges.append(charge)
    discharges.append(discharge)
    socs.append(soc)
    as_regs.append(as_reg)

# results to DataFrame
df['charge'] = charges
df['discharge'] = discharges
df['soc'] = socs
df['as_reg'] = as_regs

# Financial stuff
df['energy_revenue'] = df['discharge'] * df['rtm_price'] - df['charge'] * df['rtm_price']
df['as_revenue'] = df['as_reg'] * df['reg_price']
df['degradation_cost'] = degradation_cost * (df['charge'] + df['discharge'])
df['net_revenue'] = df['energy_revenue'] + df['as_revenue'] - df['degradation_cost']

total_profit = df['net_revenue'].sum()
annualized_profit = total_profit * 52  # 1 week to 1 year
capex = 50 * 1_200_000 + 100 * 400_000
roi = (annualized_profit / capex) * 100

# Printing
print("\n--- Rule-Based Battery Financials ---")
print(f"Total Weekly Profit:       ${total_profit:,.2f}")
print(f"Annualized Profit:         ${annualized_profit:,.2f}")
print(f"Estimated ROI:             {roi:.2f}% per year")

# Plots
fig, axs = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})

# Top plot: SOC, charge, discharge
df[['charge', 'discharge', 'soc']].plot(ax=axs[0], title="Battery Operation Over Time")
axs[0].set_ylabel("Power (MW) / Energy (MWh)")
axs[0].grid(True)

# Bottom plot: Revenue and cost breakdown
energy_revenue_total = df['energy_revenue'].sum()
as_revenue_total = df['as_revenue'].sum()
degradation_total = df['degradation_cost'].sum()
net_total = df['net_revenue'].sum()

categories = ['Energy Arbitrage', 'Regulation Reserve', 'Degradation Cost', 'Net Profit']
values = [energy_revenue_total, as_revenue_total, -degradation_total, net_total]

bars = axs[1].bar(categories, values, color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
axs[1].set_title("Battery Revenue and Cost Breakdown (1 Week)")
axs[1].set_ylabel("USD")
axs[1].grid(axis='y', linestyle='--', alpha=0.7)

# Add bar labels
for bar in bars:
    height = bar.get_height()
    axs[1].text(bar.get_x() + bar.get_width() / 2, height, f'${height:,.0f}', ha='center', va='bottom')

# Final layout
plt.tight_layout()
plt.show()