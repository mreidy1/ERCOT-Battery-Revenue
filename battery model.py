import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Simulate ERCOT-like price data
np.random.seed(42)
hours = pd.date_range(start='2025-01-01', periods=24*7, freq='h')
df = pd.DataFrame(index=hours)
# real time energy price --- normal dis around $30 change if we can get data
df['rtm_price'] = np.random.normal(loc=30, scale=10, size=len(hours)).clip(min=0) # $/MWh currently no neg prices
# regulation reserve price (ancillary services) --- normal dis around $5 change if we can get data 
df['reg_price'] = np.random.normal(loc=5, scale=2, size=len(hours)).clip(min=0) # $/MWh currently no neg prices

# Battery specs
E_max = 100   # MWh
P_max = 50    # MW
soc = 50      # Initial state of charge
eta_ch = 0.95 # Charging Efficiency 
eta_dis = 0.95 # Discharge eff
soc_min = 0.1 * E_max # min state of char
soc_max = E_max # max SoC might change to 95% for helath 
degradation_cost = 10  # $/MWh throughput
capex = 1000000000 # Battery CAPEX

# Pricing thresholds
low_price = 20   # buy (charge) if price < $20
high_price = 40  # sell (discharge) if price > $40

# Empty lists to fill 
charges, discharges, socs, as_regs = [], [], [], []

for i, row in df.iterrows():
    price = row['rtm_price']
    reg_price = row['reg_price']
    
    charge = discharge = as_reg = 0

    if price < low_price and soc < soc_max:
        charge = min(P_max, (soc_max - soc) / eta_ch) # double check this logic - would need to be sec by sec??
        soc += charge * eta_ch
    elif price > high_price and soc > soc_min:
        discharge = min(P_max, (soc - soc_min) * eta_dis) # double check this logic - would need to be sec by sec??
        soc -= discharge / eta_dis
    else:
        as_reg = 10  # Reserve 10 MWh for ancillary services - need to refine

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
df['energy_revenue'] = df['discharge'] * df['rtm_price'] - df['charge'] * df['rtm_price'] # Arbitrage rev
df['as_revenue'] = df['as_reg'] * df['reg_price'] # Ancillary rrev
df['degradation_cost'] = degradation_cost * (df['charge'] + df['discharge']) # Cost of batteru deg
df['net_revenue'] = df['energy_revenue'] + df['as_revenue'] - df['degradation_cost'] # result of aboves

total_profit = df['net_revenue'].sum() # need to add OPEX into this 
annualized_profit = total_profit * 52  # 1 week to 1 year
roi = (annualized_profit / capex) * 100

# Printing
print("\n--- Battery Financials ---")
print(f"Total Weekly Profit:       ${total_profit:,.2f}")
print(f"Annualized Profit:         ${annualized_profit:,.2f}")
print(f"Estimated ROI:             {roi:.2f}% per year")

# Plots
fig, axs = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})

# Top plot: SOC, charge, discharge, energy markets
axs[0].set_title("Battery Operation and Market Prices")

# Plot SOC, charge, and discharge
axs[0].plot(df.index, df['soc'], label='State of Charge (MWh)', color='blue')
axs[0].plot(df.index, df['charge'], label='Charge (MW)', linestyle='--', color='green')
axs[0].plot(df.index, df['discharge'], label='Discharge (MW)', linestyle='--', color='red')
axs[0].set_ylabel("Power (MW) / Energy (MWh)")
axs[0].grid(True)

# Add secondary y-axis for prices
ax2 = axs[0].twinx()
ax2.plot(df.index, df['rtm_price'], label='RTM Price ($/MWh)', color='orange', alpha=0.6)
ax2.plot(df.index, df['reg_price'], label='Reg Price ($/MW)', color='purple', alpha=0.6)
ax2.set_ylabel("Market Price ($)")
ax2.legend(loc='upper right')

# Combine legends
lines, labels = axs[0].get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
axs[0].legend(lines + lines2, labels + labels2, loc='upper left')

# Bottom plot: Revenue and cost breakdown
energy_revenue_total = df['energy_revenue'].sum()
as_revenue_total = df['as_revenue'].sum()
degradation_total = df['degradation_cost'].sum()
net_total = df['net_revenue'].sum()

categories = ['Energy Arbitrage', 'Ancillary Services', 'Degradation Cost', 'Net Profit']
values = [energy_revenue_total, as_revenue_total, -degradation_total, net_total]

bars = axs[1].bar(categories, values, color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
axs[1].set_title("Battery Revenue and Cost Breakdown")
axs[1].set_ylabel("USD")
axs[1].grid(axis='y', linestyle='--', alpha=0.7)

# Add bar labels
for bar in bars:
    height = bar.get_height()
    axs[1].text(bar.get_x() + bar.get_width() / 2, height, f'${height:,.0f}', ha='center', va='bottom')

# Final layout
plt.tight_layout()
plt.show()