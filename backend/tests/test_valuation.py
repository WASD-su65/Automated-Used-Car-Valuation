from valuation import (
    class_names, class_price, price_deduction, get_base_price, get_area,
    get_severity, calculate_price, summarize_votes,
)


def test_class_tables_have_same_length():
    assert len(class_names) == len(class_price)


def test_base_price_known_and_unknown():
    assert get_base_price("BMW_X1_2016") == 430000
    assert get_base_price("Honda_City_2014") == 170000
    assert get_base_price("Not_A_Car") == 0


def test_area():
    assert get_area([0, 0, 10, 20]) == 200
    assert get_area([5, 5, 15, 10]) == 50


def test_severity_scratch_boundary():
    assert get_severity("scratch", 2.99) == "minor"
    assert get_severity("scratch", 3.0) == "major"
    assert get_severity("scratch", 10) == "major"


def test_severity_dent_boundary():
    assert get_severity("dent", 1.49) == "minor"
    assert get_severity("dent", 1.5) == "major"


def test_severity_unknown_type_is_minor():
    assert get_severity("crack", 99) == "minor"


def test_price_no_damage():
    breakdown, deduction, final = calculate_price(300000, [], price_deduction)
    assert breakdown == {}
    assert deduction == 0
    assert final == 300000


def test_price_single_minor_scratch():
    damage = [{"Type": "scratch", "Severity": "minor"}]
    breakdown, deduction, final = calculate_price(300000, damage, price_deduction)
    assert breakdown == {"scratch_minor": 1}
    assert deduction == 2000
    assert final == 298000


def test_price_same_damage_is_counted_together():
    damage = [{"Type": "scratch", "Severity": "minor"}] * 2
    breakdown, deduction, final = calculate_price(300000, damage, price_deduction)
    assert breakdown == {"scratch_minor": 2}
    assert deduction == 4000
    assert final == 296000


def test_price_mixed_damage():
    damage = [
        {"Type": "scratch", "Severity": "major"},
        {"Type": "dent", "Severity": "minor"},
        {"Type": "dent", "Severity": "major"},
    ]
    breakdown, deduction, final = calculate_price(200000, damage, price_deduction)
    assert breakdown == {"scratch_major": 1, "dent_minor": 1, "dent_major": 1}
    assert deduction == 4000 + 4000 + 5000
    assert final == 200000 - 13000


def test_price_unknown_damage_type_has_no_deduction():
    damage = [{"Type": "crack", "Severity": "major"}]
    _, deduction, final = calculate_price(100000, damage, price_deduction)
    assert deduction == 0
    assert final == 100000


def test_votes_all_agree():
    assert summarize_votes(["A", "A", "A", "A"]) == ("4/4 sides agree", True)


def test_votes_three_of_four():
    assert summarize_votes(["A", "A", "A", "B"]) == ("3/4 sides agree", True)


def test_votes_two_of_four_is_not_reliable():
    assert summarize_votes(["A", "A", "B", "C"]) == ("2/4 sides agree", False)
    assert summarize_votes(["A", "A", "B", "B"]) == ("2/4 sides agree", False)


def test_votes_all_different():
    assert summarize_votes(["A", "B", "C", "D"]) == ("1/4 sides agree", False)