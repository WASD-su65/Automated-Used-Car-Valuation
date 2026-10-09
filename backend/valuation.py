from collections import Counter

class_price = [430000, 300000, 300000, 170000,
               200000, 170000, 290000, 580000,
               290000, 220000, 200000]

class_names = ['BMW_X1_2016', 'Ford_Renger_2016', 'Ford_Renger_2019', 'Honda_City_2014',
               'Honda_City_2016', 'Honda_Civic_2013', 'Hyundai_H1_2012', 'Hyundai_H1_2019',
               'Toyota_Fortuner_2011', 'Toyota_Revo_2015', 'Toyota_Vigo_2014']

ZOOM_LEVEL_OPTIONS = {"close": 0.10, "medium": 0.25, "wide": 0.50}

price_deduction = {
    "scratch": {"minor": 2000, "major": 4000},
    "dent":    {"minor": 4000, "major": 5000},
}

SEVERITY_THRESHOLD_PERCENT = {"scratch": 3.0, "dent": 1.5}


def get_base_price(car_class_name):
    try:
        idx = class_names.index(car_class_name)
        return class_price[idx]
    except ValueError:
        return 0


def get_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def get_severity(dtype, real_percent):
    threshold = SEVERITY_THRESHOLD_PERCENT.get(dtype, float("inf"))
    return "major" if real_percent >= threshold else "minor"


def calculate_price(base_price, damage_list, price_deduction):
    breakdown = {}
    total_deduction = 0

    for d in damage_list:
        key = f"{d['Type']}_{d['Severity']}"
        breakdown[key] = breakdown.get(key, 0) + 1

    for key, count in breakdown.items():
        dtype, severity = key.rsplit("_", 1)
        deduction_per_point = price_deduction.get(dtype, {}).get(severity, 0)
        total_deduction += count * deduction_per_point

    final_price = base_price - total_deduction
    return breakdown, total_deduction, final_price


def summarize_votes(classes):
    total = len(classes)
    top_count = Counter(classes).most_common(1)[0][1]
    agreement = f"{top_count}/{total} sides agree"
    reliable = top_count >= (total // 2 + 1)
    return agreement, reliable