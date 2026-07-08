def calculate_wellness_score(prod, stress, hours, salary, break_freq):
    """
    Calculates a composite wellness score (0-100) and status.
    Formula: 0.30*Prod + 0.25*(10-Stress)*10 + 0.20*(Hours Balance) + 0.15*(Salary Satisfaction) + 0.10*(Break Frequency)
    """
    # 1. Stress component (inverted)
    stress_comp = (10 - stress) * 10 
    
    # 2. Hours balance (Ideal 8h)
    hours_comp = 100 - abs(8 - hours) * 10
    hours_comp = max(0, min(100, hours_comp))
    
    # 3. Salary satisfaction (Mock normalized)
    salary_comp = min(100, (salary / 1000))
    
    # 4. Break frequency (Normalized)
    break_comp = min(100, break_freq * 400) # e.g. 0.25 * 400 = 100
    
    score = (0.30 * prod) + (0.25 * stress_comp) + (0.20 * hours_comp) + (0.15 * salary_comp) + (0.10 * break_comp)
    score = round(max(0, min(100, score)), 1)
    
    status = "Healthy"
    if score < 40: status = "Burnout"
    elif score < 60: status = "Risk"
    elif score < 80: status = "Moderate"
    
    return score, status
