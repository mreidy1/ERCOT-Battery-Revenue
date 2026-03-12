import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os

# ========================= LOAD AND CLEAN HISTORICAL DATA =========================

folder_path = r'C:\Users\Marcu\OneDrive - Imperial College London\Clean Tech\Data for Modelling'
all_files = glob.glob(os.path.join(folder_path, '*.xlsx'))

print("Loading historical data...")

df_list = []
for file in all_files:  
    xls = pd.ExcelFile(file)
    for sheet_name in xls.sheet_names:
        try:
            df_temp = pd.read_excel(xls, sheet_name=sheet_name)
            if not df_temp.empty:
                df_temp['source_file'] = os.path.basename(file)
                df_temp['sheet_name'] = sheet_name
                df_list.append(df_temp)
        except Exception as e:
            print(f"Failed to read {sheet_name} in {file}: {e}")

df_combined = pd.concat(df_list, ignore_index=True)
print("Files loaded and combined.")

# ========================= PARSE TIMESTAMPS =========================

df_combined['Delivery Date'] = pd.to_datetime(df_combined['Delivery Date'])
df_combined['base_hour'] = df_combined['Delivery Hour'] - 1
df_combined['minutes'] = (df_combined['Delivery Interval'] - 1) * 15
df_combined['timestamp'] = df_combined['Delivery Date'] + pd.to_timedelta(df_combined['base_hour'], unit='h') + pd.to_timedelta(df_combined['minutes'], unit='m')

df = df_combined[['timestamp', 'Settlement Point Name', 'Settlement Point Price']].copy()
df.rename(columns={'Settlement Point Name': 'zone', 'Settlement Point Price': 'rtm_price'}, inplace=True)
df.set_index('timestamp', inplace=True)
df.sort_index(inplace=True)

# ========================= FEATURE ENGINEERING =========================

df['hour'] = df.index.hour
df['month'] = df.index.month
df['date'] = df.index.date
df['day'] = df.index.day
df['weekday'] = df.index.weekday
df['year'] = df.index.year

def get_season(month):
    if month in [12, 1, 2]: return 'Winter'
    elif month in [3, 4, 5]: return 'Spring'
    elif month in [6, 7, 8]: return 'Summer'
    else: return 'Autumn'
df['season'] = df['month'].apply(get_season)

zones_to_include = ['LZ_HOUSTON', 'LZ_WEST', 'LZ_NORTH', 'LZ_SOUTH']
df_filtered = df[df['zone'].isin(zones_to_include)].copy()

# ========================= HOURLY BOXPLOT =========================

plt.figure(figsize=(14, 6))
sns.boxplot(x='hour', y='rtm_price', hue='zone', data=df_filtered, palette='muted', showfliers=False)
plt.title('ERCOT RTM Price Distribution by Hour (2020–2024)')
plt.xlabel('Hour of Day')
plt.ylabel('RTM Price ($/MWh)')
plt.ylim(-100, 200)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(title='Load Zone')
plt.tight_layout()
plt.show()

# ========================= GRAPH 1: DAILY TIME SERIES FOR LZ_HOUSTON =========================

houston_df = df[df['zone'] == 'LZ_HOUSTON']
houston_daily = houston_df['rtm_price'].resample('D').mean()

plt.figure(figsize=(15, 5))
plt.plot(houston_daily.index, houston_daily.values, label='Daily Avg RTM Price (LZ_HOUSTON)', color='blue')
plt.title('LZ_HOUSTON RTM Prices (2020–2024)')
plt.xlabel('Date')
plt.ylabel('RTM Price ($/MWh)')
plt.grid(True)
plt.tight_layout()
plt.legend()
plt.show()

# ========================= GRAPH 2A: MONTHLY SHAPE FACTORS =========================

monthly_avg = houston_df['rtm_price'].groupby([houston_df.index.year, houston_df.index.month]).mean().unstack()
yearly_avg = monthly_avg.mean(axis=1)
shape_factors = monthly_avg.div(yearly_avg, axis=0)

plt.figure(figsize=(10, 5))
for year in shape_factors.index:
    plt.plot(shape_factors.columns, shape_factors.loc[year], label=str(year))
plt.title('Monthly Shape Factors by Year (LZ_HOUSTON)', fontsize=14)
plt.xlabel('Month')
plt.ylabel('Shape Factor (Normalized)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# ========================= GRAPH 2B: MONTHLY VOLATILITY (MAD) =========================

mad = houston_df['rtm_price'].groupby([houston_df.index.year, houston_df.index.month]).apply(lambda x: x.mad()).unstack()

plt.figure(figsize=(10, 5))
for year in mad.index:
    plt.plot(mad.columns, mad.loc[year], label=str(year))
plt.title('Monthly RTM Price Volatility (MAD) – LZ_HOUSTON')
plt.xlabel('Month')
plt.ylabel('MAD ($/MWh)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()