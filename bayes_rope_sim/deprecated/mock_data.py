import pandas as pd
import numpy as np

def create_mock_data(baseline_cr=.1, mde=.01, daily_sample_size=100, num_days=45, noise_level=5, start_date='2025-01-01'):
    # lists to hold the data
    groups = []
    conversions = []
    observations = []
    dates = []
    
    # Convert start_date to datetime
    current_date = pd.to_datetime(start_date)
    
    # Generate data for each day
    for day in range(num_days):
        # Alternate between 'control' and 'treatment'
        for group in ['control', 'treatment']:
            # Add some random noise to the daily sample size 
            observation_count = np.random.normal(daily_sample_size, noise_level)
            observation_count = max(1, int(round(observation_count)))  # Ensure a positive integer
            
            # Define the conversion rate for each group
            if group == 'control':
                conversion_rate = baseline_cr
            else:
                # Apply mde (minimum detectable effect) to group 'treatment'
                conversion_rate = baseline_cr * (1 + mde)
            
            # Simulate conversions using binomial distribution
            conversion = np.random.binomial(observation_count, conversion_rate)
            
            # Append the generated data
            groups.append(group)
            conversions.append(conversion)
            observations.append(observation_count)
            dates.append(current_date)
        
        # Increment the date by one day after each iteration
        current_date += pd.Timedelta(days=1)
    
    # Create the dataframe
    df = pd.DataFrame({
        'group': groups,
        'conversion': conversions,
        'observation': observations,
        'date': dates
    })
    
    return df