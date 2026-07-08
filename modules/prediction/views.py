import logging
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
import json
import os
from modules.utils import calculate_wellness_score

logger = logging.getLogger(__name__)

# Lazy loading for models
_ml_resources = {
    'scaler': None,
    'stress_model': None,
    'burnout_model': None,
    'productivity_model': None,
    'loaded': False
}

def get_ml_resources():
    if not _ml_resources['loaded']:
        import joblib
        MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
        try:
            _ml_resources['scaler'] = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
            _ml_resources['stress_model'] = joblib.load(os.path.join(MODEL_DIR, 'stress_model.pkl'))
            _ml_resources['burnout_model'] = joblib.load(os.path.join(MODEL_DIR, 'burnout_model.pkl'))
            _ml_resources['productivity_model'] = joblib.load(os.path.join(MODEL_DIR, 'productivity_model.pkl'))
            _ml_resources['loaded'] = True
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
    return _ml_resources

def prepare_features(data):
    resources = get_ml_resources()
    if not resources['loaded']:
        return None
        
    # Match the features list from training
    features = ['hours_worked', 'tasks_completed', 'attendance_rate', 'basic', 'hra', 'ta', 'da', 
                'mental_fatigue', 'break_time', 'work_efficiency', 'salary_total', 'burnout_index']
    
    # Calculate derived features if not present
    if 'work_efficiency' not in data:
        data['work_efficiency'] = data.get('tasks_completed', 20) / max(data.get('hours_worked', 40), 1)
    if 'salary_total' not in data:
        data['salary_total'] = data.get('basic', 0) + data.get('hra', 0) + data.get('ta', 0) + data.get('da', 0)
    if 'burnout_index' not in data:
        data['burnout_index'] = data.get('mental_fatigue', 5) * data.get('hours_worked', 40) / 100.0
        
    # Extract values in correct order
    feature_values = [[data.get(f, 0) for f in features]]
    
    # Scale features
    scaler = resources.get('scaler')
    if scaler is None:
        return None
    return scaler.transform(feature_values)

@csrf_exempt
def predict_api(request):
    from django.http import JsonResponse
    from database.models import Employee
    
    resources = get_ml_resources()
    if not resources['loaded']:
        return JsonResponse({"error": "ML models are currently not loaded."}, status=503)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            X_scaled = prepare_features(data)
            if X_scaled is None:
                 return JsonResponse({"error": "Failed to prepare features."}, status=500)
            
            # Extract basic info for extended AI features
            employee_id = data.get('emp_id')
            employee = None
            if employee_id:
                try:
                    employee = Employee.objects.get(emp_id=employee_id)
                except Employee.DoesNotExist:
                    pass
            
            # Predict core metrics
            stress_model = resources.get('stress_model')
            burnout_model = resources.get('burnout_model')
            productivity_model = resources.get('productivity_model')
            
            if not all([stress_model, burnout_model, productivity_model]):
                 return JsonResponse({"error": "ML models are not correctly initialized."}, status=500)

            stress = float(stress_model.predict(X_scaled)[0])
            burnout = int(burnout_model.predict(X_scaled)[0])
            productivity = float(productivity_model.predict(X_scaled)[0])
            
            # 1. Anomaly Detection
            if employee:
                anomaly_score, risk_label, is_anomaly = detect_anomaly(employee)
            else:
                anomaly_score, risk_label, is_anomaly = 0.0, "Unknown", False
                
            # 2. Wellness Score
            hours = data.get('hours_worked', 40) / 5.0 # roughly daily
            salary = data.get('basic', 0) + data.get('hra', 0)
            break_freq = data.get('break_time', 0) / max(hours, 1)
            wellness_score, w_status = calculate_wellness_score(productivity, stress, hours, salary, break_freq)
            
            # 3. Recommendations
            recommendations = get_recommendations(stress, hours, (salary/50000)*100, is_anomaly)

            return JsonResponse({
                "stress": float(f"{stress:.2f}"),
                "burnout": "High Risk" if burnout == 1 else "Low Risk",
                "productivity": float(f"{productivity:.2f}"),
                "anomaly_score": anomaly_score,
                "anomaly_risk": risk_label,
                "wellness_score": wellness_score,
                "wellness_status": w_status,
                "recommendations": recommendations
            })
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

def webcam_view(request):
    """Render the webcam capture page."""
    return render(request, 'prediction/webcam.html')

@csrf_exempt
def emotion_analyze_api(request):
    """Analyze base64 image from webcam to detect emotion and assign stress score."""
    from django.http import JsonResponse
    if request.method == 'POST':
        try:
            import numpy as np
            import cv2
            from deepface import DeepFace
            from modules.utils import ensure_ai_weights
            
            # 1. Self-healing for weights
            ensure_ai_weights()
            
            data = json.loads(request.body)
            image_b64 = data.get('image', '')
            
            if not image_b64:
                return JsonResponse({"error": "No image data provided"}, status=400)
                
            # Strip the 'data:image/jpeg;base64,' prefix 
            if ',' in image_b64:
                image_b64 = image_b64.split(',')[1]
                
            # Decode base64 to image
            image_data = base64.b64decode(image_b64)
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return JsonResponse({"error": "Invalid image format"}, status=400)
            
            # analyze returns a list of dictionaries if multiple faces are found
            result = DeepFace.analyze(img, actions=['emotion'], detector_backend="retinaface",enforce_detection=True)
            
            if isinstance(result, list):
                res = result[0]
            else:
                res = result
                
            emotions = res['emotion']
            dominant_emotion = res['dominant_emotion']
            
            # Log all emotions for debugging
            logger.info(f"Raw emotions: {emotions}")
            
            # Map emotion to stress score
            emotion_stress_map = {
                'angry': (9, 'High Stress / Frustrated'),
                'disgust': (8, 'Frustrated'),
                'fear': (8, 'Anxious / High Pressure'),
                'sad': (7, 'Low Mood / Possible Burnout'),
                'neutral': (4, 'Stable / Focused'),
                'surprise': (4, 'Alert / Reactive'),
                'happy': (2, 'Optimal / Highly Satisfied')
            }
            
            stress_score, interpretation = emotion_stress_map.get(dominant_emotion.lower(), (5, 'Unknown'))
            
            # If neutral is dominant but something else is very close (e.g. within 10%), 
            # we might want to mention it. But for now, let's just make the labels more premium.
            
            return JsonResponse({
                "emotion": dominant_emotion.capitalize(),
                "stress_score": int(stress_score),
                "interpretation": interpretation,
                "raw_scores": {k: float(f"{v:.2f}") for k, v in emotions.items()}
            })
            
        except Exception as e:
            logger.error(f"Emotion analysis error: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)

def detect_anomaly(employee):
    """
    Detects unusual work patterns using Isolation Forest on historical data.
    Returns (anomaly_score, risk_label, is_anomaly).
    """
    try:
        from database.models import WellnessLog, ProductivityLog
        from sklearn.ensemble import IsolationForest
        import numpy as np
        
        # Fetch historical wellness and productivity logs
        w_logs = list(WellnessLog.objects.filter(employee=employee).order_by('-date')[:30])
        p_logs = list(ProductivityLog.objects.filter(employee=employee).order_by('-date')[:30])
        
        if len(w_logs) < 5 or len(p_logs) < 5:
            return 0.0, "Insufficient Data", False
            
        # Create a simple dataset of (hours_worked, mental_fatigue, efficiency_score)
        # We assume dates roughly align for simplicity in this demo
        data = []
        for i in range(min(len(w_logs), len(p_logs))):
            data.append([
                w_logs[i].hours_worked, 
                w_logs[i].mental_fatigue,
                p_logs[i].efficiency_score or 0  # handling None
            ])
            
        X = np.array(data)
        
        # Train Isolation Forest on this employee's history to learn their "normal"
        clf = IsolationForest(contamination=0.1, random_state=42)
        clf.fit(X)
        
        # Predict on the most recent log
        latest_point = X[0].reshape(1, -1)
        prediction = clf.predict(latest_point)[0] # 1 for normal, -1 for anomaly
        score = clf.score_samples(latest_point)[0] # raw anomaly score (negative, lower is more anomalous)
        
        # Normalize score roughly to 0-1 for display
        normalized_score = min(max((score + 0.8) / 0.8, 0.0), 1.0)
        
        # Invert so 1.0 is highly anomalous, 0.0 is normal
        anomaly_score = 1.0 - normalized_score 
        
        is_anomaly = prediction == -1
        risk_label = "High Risk (Unusual Pattern Detected)" if is_anomaly else "Normal Pattern"
        
        return float(f"{anomaly_score:.2f}"), risk_label, is_anomaly
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        return 0.0, "Error", False

def get_recommendations(stress_level, work_hours, salary_sat_score, is_anomaly):
    """Rule-based recommendations based on AI outputs"""
    recs = []
    
    if stress_level > 7:
        recs.append("Suggest mandatory short breaks every 2 hours.")
    
    if work_hours > 9:
        recs.append("Recommend immediate workload balancing and NO overtime.")
        
    if salary_sat_score < 50:
        recs.append("Flag for HR comp review during next performance cycle.")
        
    if is_anomaly:
        recs.append("Unusual work pattern detected. Schedule an informal 1-on-1 check-in.")
        
    if not recs:
        recs.append("Keep up the good work! No immediate actions required.")
        
    return recs

@csrf_exempt
def repair_ai_models(request):
    """
    Utility endpoint to clear corrupted DeepFace model weights.
    Only accessible via SuperAdmin in UI.
    """
    from modules.utils import ensure_ai_weights
    status, message, details = ensure_ai_weights()
    return JsonResponse({
        "status": "success" if status else "error",
        "message": message,
        "details": details
    })

