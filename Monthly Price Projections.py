import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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

# ========================= FILTER ZONES & CLIP EXTREMES =========================

zones_of_interest = ['LZ_HOUSTON']
df_focus = df[df['zone'].isin(zones_of_interest)].copy()

# Cap outlier prices to $0–$500
df_focus['rtm_price'] = df_focus['rtm_price'].clip(lower=0, upper=500)

# ========================= SMOOTH HISTORICAL RTM PRICES =========================

df_focus['rtm_price_smooth'] = df_focus['rtm_price'].rolling(window=96*30, center=True, min_periods=96).mean()

# ========================= MONTHLY SHAPE FACTORS =========================

df_hist = df_focus.copy()
df_hist['year'] = df_hist.index.year
df_hist['month'] = df_hist.index.month

monthly_avg = df_hist.groupby(['year', 'month'])['rtm_price_smooth'].mean().reset_index()
yearly_avg = df_hist.groupby('year')['rtm_price_smooth'].mean().reset_index()
monthly_avg = pd.merge(monthly_avg, yearly_avg, on='year', suffixes=('', '_year'))

monthly_avg['shape_factor'] = monthly_avg['rtm_price_smooth'] / monthly_avg['rtm_price_smooth_year']
seasonal_factors = monthly_avg.groupby('month')['shape_factor'].mean()

# ========================= MAD-BASED VOLATILITY =========================

monthly_mad = (
    df_focus
    .groupby(['year', 'month'])['rtm_price']
    .apply(lambda x: np.median(np.abs(x - np.median(x))))
)

monthly_mad_avg = monthly_mad.groupby('month').mean()

# Clip volatility range
std_clip_min = monthly_mad_avg.quantile(0.1)
std_clip_max = monthly_mad_avg.quantile(0.9)
monthly_std_clipped = monthly_mad_avg.clip(lower=std_clip_min, upper=std_clip_max)

# ========================= LOAD FORECAST DATA =========================

forecast_excel_path = r"C:\Users\Marcu\OneDrive - Imperial College London\Clean Tech\yearly price predictions (modo).xlsx"
forecast_data = pd.read_excel(forecast_excel_path)

forecast_data.columns = forecast_data.columns.str.strip()
forecast_df = forecast_data.rename(columns={'Year': 'year', 'Houston': 'price'})[['year', 'price']]
forecast_df = forecast_df[forecast_df['year'] >= 2024]

# ========================= GENERATE FORECAST WITH NOISE =========================

monthly_forecast = []

for _, row in forecast_df.iterrows():
    year = row['year']
    base_price = row['price']
    
    for month in range(1, 13):
        shape = seasonal_factors.loc[month]
        noise = np.random.normal(loc=0, scale=monthly_std_clipped.loc[month] * 0.5)
        monthly_price = base_price * shape + noise
        
        monthly_forecast.append({
            'year': year,
            'month': month,
            'base_price': round(base_price, 2),
            'shape_factor (monthly/yearly)': round(shape, 4),
            'noise': round(noise, 2),
            'forecasted_price': round(monthly_price, 2)
        })

forecast_monthly_df = pd.DataFrame(monthly_forecast)

# Smooth forecast further if needed
forecast_monthly_df['forecasted_price'] = forecast_monthly_df['forecasted_price'].rolling(window=3, center=True, min_periods=1).mean()

# Create datetime index
forecast_monthly_df['day'] = 1
forecast_monthly_df['date'] = pd.to_datetime(forecast_monthly_df[['year', 'month', 'day']])
forecast_monthly_df.set_index('date', inplace=True)

# ========================= EXPORT TO EXCEL =========================

output_path = r"C:\Users\Marcu\OneDrive - Imperial College London\Clean Tech\Forecasted_Monthly_Prices.xlsx"
forecast_monthly_df.to_excel(output_path, index=False)
print(f"Monthly forecast with noise saved to:\n{output_path}")

# ========================= PLOTTING =========================

historical_monthly = df_focus.resample('M')['rtm_price'].mean().to_frame()
historical_monthly.index = historical_monthly.index.to_period('M').to_timestamp()
historical_monthly = historical_monthly.rename(columns={'rtm_price': 'price'})

forecast_clean = forecast_monthly_df[['forecasted_price']].rename(columns={'forecasted_price': 'price'})
combined = pd.concat([historical_monthly, forecast_clean])

plt.figure(figsize=(14, 6))
plt.plot(combined.index, combined['price'], label='Historical', color='dodgerblue')

# Add raw yearly forecast points
plt.scatter(
    pd.to_datetime(forecast_df['year'].astype(str) + '-07-01'),
    forecast_df['price'],
    color='black',
    marker='o',
    label='Raw Yearly Forecast',
    zorder=3
)

plt.axvline(pd.to_datetime('2024-01-01'), color='red', linestyle='--', label='Forecast')
plt.title('ERCOT LZ_HOUSTON: Monthly RTM Prices (Historical + Forecast)')
plt.ylabel('Price ($/MWh)')
plt.xlabel('Date')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()