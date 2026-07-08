import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import joblib
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.feature_engineering import generate_synthetic_data, engineer_features

def train_models():
    print("Loading data...")
    dataset_path = 'dataset/synthetic_employee_data.csv'
    
    # Generate data if missing
    if not os.path.exists(dataset_path):
        os.makedirs('dataset', exist_ok=True)
        raw_df = generate_synthetic_data(1000)
        df = engineer_features(raw_df)
        df.to_csv(dataset_path, index=False)
    else:
        df = pd.read_csv(dataset_path)

    # Features
    features = ['hours_worked', 'tasks_completed', 'attendance_rate', 'basic', 'hra', 'ta', 'da', 
                'mental_fatigue', 'break_time', 'work_efficiency', 'salary_total', 'burnout_index']
    
    X = df[features]
    
    # Targets
    y_stress = df['stress_score']
    y_burnout = df['burnout_label']
    y_productivity = df['productivity_score']
    
    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Save Scaler
    os.makedirs('ml_models', exist_ok=True)
    joblib.dump(scaler, "ml_models/scaler.pkl")

    # Train Stress Model (Regressor)
    print("Training Stress Model...")
    stress_model = RandomForestRegressor(n_estimators=100, random_state=42)
    stress_model.fit(X_scaled, y_stress)
    joblib.dump(stress_model, "ml_models/stress_model.pkl")

    # Train Burnout Model (Classifier)
    print("Training Burnout Model...")
    burnout_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    burnout_model.fit(X_scaled, y_burnout)
    joblib.dump(burnout_model, "ml_models/burnout_model.pkl")

    # Train Productivity Model (Regressor)
    print("Training Productivity Model...")
    prod_model = LinearRegression()
    prod_model.fit(X_scaled, y_productivity)
    joblib.dump(prod_model, "ml_models/productivity_model.pkl")

    print("All models trained and saved to ml_models/ directory successfully.")

if __name__ == "__main__":
    train_models()

