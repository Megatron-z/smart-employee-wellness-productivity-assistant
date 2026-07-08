from django.urls import path
from modules.prediction import views

urlpatterns = [
    path('predict/', views.predict_api, name='predict_api'),
    path('emotion-analyze/', views.emotion_analyze_api, name='emotion_analyze_api'),
    path('webcam/', views.webcam_view, name='webcam_view'),
    path('repair-ai/', views.repair_ai_models, name='repair_ai_models'),
]
