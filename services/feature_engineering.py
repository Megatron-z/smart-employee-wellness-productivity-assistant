import pandas as pd
import numpy as np

def generate_synthetic_data(n=1000):
    np.random.seed(42)
    data = {
        'employee_id': range(1, n + 1),
        'hours_worked': np.random.uniform(30, 60, n),
        'tasks_completed': np.random.randint(5, 50, n),
        'attendance_rate': np.random.uniform(0.7, 1.0, n),
        'basic': np.random.uniform(20000, 50000, n),
        'hra': np.random.uniform(5000, 15000, n),
        'ta': np.random.uniform(2000, 5000, n),
        'da': np.random.uniform(1000, 3000, n),
        'mental_fatigue': np.random.uniform(1, 10, n),
        'break_time': np.random.uniform(0.5, 2.0, n),
    }
    return pd.DataFrame(data)

def engineer_features(df):
    # Calculate derived features
    df['salary_total'] = df['basic'] + df['hra'] + df['ta'] + df['da']
    df['work_efficiency'] = (df['tasks_completed'] / df['hours_worked']) * 10
    
    # Synthetic target generation logic
    df['stress_score'] = (df['mental_fatigue'] * 0.5 + (60 - df['hours_worked']) * 0.1 + np.random.normal(0, 1, len(df))).clip(1, 10)
    df['burnout_index'] = (df['stress_score'] * 0.7 + (df['hours_worked'] / 10) * 0.3).clip(0, 10)
    df['burnout_label'] = (df['burnout_index'] > 7).astype(int)
    
    # Productivity score logic
    df['productivity_score'] = (df['work_efficiency'] * 0.6 + df['attendance_rate'] * 40 + np.random.normal(0, 5, len(df))).clip(0, 100)
    
    return df
