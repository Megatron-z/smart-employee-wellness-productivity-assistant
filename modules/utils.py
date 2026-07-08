def calculate_wellness_score(productivity, stress, hours, salary_factor, break_freq):
    """
    Calculates a wellness score based on various employee metrics.
    
    Args:
        productivity (float): Productivity score (0-100)
        stress (float): Stress level (0-10)
        hours (float): Hours worked (typical daily: 8)
        salary_factor (float): Relative salary satisfaction/level (0-100)
        break_freq (float): Breaks per hour
        
    Returns:
        tuple: (score, status) where score is 0-100 and status is a string description.
    """
    # Base score starts with productivity
    score = productivity * 0.4
    
    # Stress penalty (inverted stress 0-10 -> 10-0, then scaled to 30 points)
    stress_impact = (10 - min(max(stress, 0), 10)) * 3
    score += stress_impact
    
    # Work-life balance impact (target 8 hours)
    if hours <= 9:
        wlb_impact = 15
    elif hours <= 11:
        wlb_impact = 10
    else:
        wlb_impact = 5
    score += wlb_impact
    
    # Salary factor (up to 10 points)
    score += (min(max(salary_factor, 0), 100) / 10.0)
    
    # Break frequency (up to 5 points)
    score += min(break_freq * 10, 5)
    
    # Normalize score to 0-100
    final_score = float(round(min(max(score, 0), 100), 2))
    
    # Determine status
    if final_score >= 80:
        status = "Excellent - Thriving"
    elif final_score >= 60:
        status = "Good - Stable"
    elif final_score >= 40:
        status = "Fair - Needs Attention"
    else:
        status = "Critical - At Risk"
        
    return final_score, status

def ensure_ai_weights():
    """
    Checks for the presence and integrity of DeepFace model weights.
    If a weight file is corrupted (e.g. 0 bytes or very small), it deletes it 
    to force DeepFace to re-download.
    
    Returns:
        tuple: (success, message, details)
    """
    import os
    from pathlib import Path
    
    home = str(Path.home())
    weights_dir = os.path.join(home, '.deepface', 'weights')
    
    if not os.path.exists(weights_dir):
        return True, "Weights directory not yet created. DeepFace will create it on next run.", {}

    results = []
    issues_found = False
    
    # Common weights used in this project
    models = {
        'facial_expression_model_weights.h5': 100 * 1024, # 100KB threshold
        'vgg_face_weights.h5': 10 * 1024 * 1024,        # 10MB threshold
    }
    
    for filename, min_size in models.items():
        file_path = os.path.join(weights_dir, filename)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size < min_size:
                try:
                    os.remove(file_path)
                    results.append(f"Deleted corrupted {filename} ({size} bytes)")
                    issues_found = True
                except Exception as e:
                    results.append(f"Failed to delete corrupted {filename}: {e}")
            else:
                results.append(f"{filename} looks healthy ({round(size/1024/1024, 2)} MB)")
        else:
            results.append(f"{filename} not present (will download on demand)")

    if issues_found:
        return True, "Corrupted weights were detected and removed. They will be re-downloaded during the next AI task.", {"log": results}
    return True, "AI weights are missing or in good condition. No repairs needed.", {"log": results}
