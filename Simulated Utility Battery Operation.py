import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ================================================ Market Data =============================================================
# need the historical data here  

# Simulate 15-minute ERCOT-like price data for one week
np.random.seed(42)
timestamps = pd.date_range(start='2025-01-01', periods=24*7*4, freq='15min')
df = pd.DataFrame(index=timestamps)

# Simulated price signals
# Real Time Energy Price 
df['rtm_price'] = np.random.normal(loc=30, scale=10, size=len(df)).clip(min=0) # $/MWh currently no neg prices
# Regulation Reserve Price
df['reg_price'] = np.random.normal(loc=5, scale=2, size=len(df)).clip(min=0) # $/MWh currently no neg prices
# Responsive Reserve Service Price
df['rrs_price'] = np.random.normal(loc=4, scale=1.5, size=len(df)).clip(min=0) # $/MWh currently no neg prices
# Non-Spinning Reserve Service Price
df['nsrs_price'] = np.random.normal(loc=2, scale=1.0, size=len(df)).clip(min=0) # $/MWh currently no neg prices

# Rolling mean for dynamic price logic 96 data points for window (24 hours)
df['rolling_mean'] = df['rtm_price'].rolling(window=96, min_periods=1).mean()

# ================================================ Battery Specs =============================================================

E_max = 100 # MWh
P_max = 50 # MW
soc = 50 # Initial state of charge
eta_ch = 0.95 # Charging Efficiency 
eta_dis = 0.95  # Discharge eff
soc_min = 0.1 * E_max # min state of char
soc_max = E_max # max SoC might change to 95% for helath 
degradation_cost = 10  # $/MWh throughput
capex = 100_000_000 # Battery CAPEX

# ================================================ Charging Logic =============================================================

# Dynamic thresholds based on rolling mean
delta_low = 5 # Charge the battery if the current price is at least $5 lower than the 24-hour average
delta_high = 5 # Discharge the battery if the current price is at least $5 lower than the 24-hour average

# Empty lists to fill 
charges, discharges, socs, reg_reserves, rrs_reserves, nsrs_reserves = [], [], [], [], [], []

for i, row in df.iterrows():
    price = row['rtm_price'] # current Real Time Energy Price 
    reg_price = row['reg_price'] # current Regulation Reserve Price 
    rrs_price = row['rrs_price'] # current Responsive Reserve Service Price
    nsrs_price = row['nsrs_price'] # current Non-Spinning Reserve Service Price
    rolling_mean = row['rolling_mean'] # current mean price from last 24 hours

    # reset behaviour variables 
    charge = discharge = reg = rrs = nsrs = 0

    # Dynamic dispatch logic
    if price < rolling_mean - delta_low and soc < soc_max: 
        charge = min(P_max, (soc_max - soc) / eta_ch) # calc the max possible charging amount
        soc += charge * eta_ch # calc the delta SoC 
    elif price > rolling_mean + delta_high and soc > soc_min:
        discharge = min(P_max, (soc - soc_min) * eta_dis) # calc the max possible discharging amou8nt 
        soc -= discharge / eta_dis # calc the delta SoC 
    else:
        # reserve capacity for ancillary services to use when those prices are above thresholds, if prices arent no reserve cap
        reg = 10 if reg_price > 3 else 0
        rrs = 10 if rrs_price > 3 else 0
        nsrs = 10 if nsrs_price > 1.5 else 0

    # Save values
    charges.append(charge)
    discharges.append(discharge)
    socs.append(soc)
    reg_reserves.append(reg)
    rrs_reserves.append(rrs)
    nsrs_reserves.append(nsrs)

# Results to DataFrame
df['charge'] = charges
df['discharge'] = discharges
df['soc'] = socs
df['reg'] = reg_reserves
df['rrs'] = rrs_reserves
df['nsrs'] = nsrs_reserves

# ================================================ Financial calculations =============================================================
#  not sure if needed or just use will spreadsheet 
# needed for the aggregation so should keep 

df['energy_revenue'] = df['discharge'] * df['rtm_price'] - df['charge'] * df['rtm_price']
df['as_revenue'] = df['reg'] * df['reg_price'] + df['rrs'] * df['rrs_price'] + df['nsrs'] * df['nsrs_price']
df['degradation_cost'] = degradation_cost * (df['charge'] + df['discharge'])
df['net_revenue'] = df['energy_revenue'] + df['as_revenue'] - df['degradation_cost']

total_profit = df['net_revenue'].sum()
annualized_profit = total_profit * (365 / 7)
roi = (annualized_profit / capex) * 100

# Finanical Output summary
print("\n--- Battery Financials ---")
print(f"Total Weekly Profit:       ${total_profit:,.2f}")
print(f"Annualized Profit:         ${annualized_profit:,.2f}")
print(f"Estimated ROI:             {roi:.2f}% per year")

# Add daily revenue aggregation
df['date'] = df.index.date
daily_revenue = df.groupby('date').agg({
    'energy_revenue': 'sum',
    'as_revenue': 'sum',
    'degradation_cost': 'sum',
    'net_revenue': 'sum'
})

# ================================================ Plotting =============================================================

# Adjust degradation cost to be negative in the daily revenue breakdown
daily_revenue['degradation_cost'] = -daily_revenue['degradation_cost']

# 2x2 dashboard 
fig, axs = plt.subplots(2, 2, figsize=(16, 10))

# Top Left: Battery operation
# need to double charge the units are correct 
axs[0, 0].set_title("Battery State of Charge and Dispatch")
axs[0, 0].plot(df.index, df['soc'], label='State of Charge (MWh)', color='blue')
axs[0, 0].plot(df.index, df['charge'], label='Charge (MW)', linestyle='--', color='green')
axs[0, 0].plot(df.index, df['discharge'], label='Discharge (MW)', linestyle='--', color='red')
axs[0, 0].set_ylabel("MW / MWh")
axs[0, 0].legend()
axs[0, 0].grid(True)

# Top Right: Market Prices
# Do I need to change the labels?
axs[0, 1].set_title("Market Price Signals")
axs[0, 1].plot(df.index, df['rtm_price'], label='RTM Price', color='orange', alpha=0.6)
axs[0, 1].plot(df.index, df['reg_price'], label='Reg Price', color='purple', alpha=0.6)
axs[0, 1].plot(df.index, df['rrs_price'], label='RRS Price', color='brown', alpha=0.6)
axs[0, 1].plot(df.index, df['nsrs_price'], label='NSRS Price', color='gray', alpha=0.6)
axs[0, 1].set_ylabel("$/MWh")
axs[0, 1].legend()
axs[0, 1].grid(True)

# Bottom Left: Daily revenue breakdown 
daily_revenue.plot(kind='bar', stacked=True, ax=axs[1, 0], color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
axs[1, 0].set_title("Daily Revenue Breakdown")
axs[1, 0].set_ylabel("USD")
axs[1, 0].set_xlabel("Date")
axs[1, 0].tick_params(axis='x', rotation=45)
axs[1, 0].legend(loc='upper right')
axs[1, 0].grid(True)

# Bottom Right: Total financials
revenue_totals = [
    df['energy_revenue'].sum(),
    df['as_revenue'].sum(),
    -df['degradation_cost'].sum(), # in a differnet dataframe to daily rev breakdown which is why it needs to be negative
    df['net_revenue'].sum()
]
categories = ['Energy Arbitrage', 'Ancillary Services', 'Degradation Cost', 'Net Profit']
bars = axs[1, 1].bar(categories, revenue_totals, color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
axs[1, 1].set_title("Total Financial Summary (1 Week)")
axs[1, 1].set_ylabel("USD")
axs[1, 1].grid(axis='y', linestyle='--', alpha=0.7)
for bar in bars:
    height = bar.get_height()
    axs[1, 1].text(bar.get_x() + bar.get_width() / 2, height, f'${height:,.0f}', ha='center', va='bottom')

plt.tight_layout()
plt.show()