ERCOT Battery Revenue model - Imperial 

Overivew
This project as part of my masters was to examine the investablility of a utlitiy scale battery in the US.  The model combines historical real-time market data with a forward price simulation to generate 15-minute price paths and evaluate battery dispatch strategies.It evaluates revenue streams including energy arbitrage and ancillary services while accounting for operational constraints such as power limits, state of charge, degradation, and cycling limits.

Architecture
1. Load historical ERCOT RTM price data
2. Extract seasonal patterns and volatility
3. Generate forward price paths using ARMA noise + seasonal factors
4. Simulate battery dispatch with:
      arbitrage strategy
      ancillary services participation
      degradation constraints
5. Output revenue projections and operational metrics

Battery Assumptions
Parameter	                  Value
Energy Capacity	            240 MWh
Power Capacity	            60 MW
Round-trip Efficiency	      85%
Minimum SOC	                  10%
Maximum Cycles	            1 per day
Degradation Cost	            $10/MWh throughput


