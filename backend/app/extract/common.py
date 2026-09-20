from datetime import datetime


def week_start_date(year: int, week_number: int) -> datetime:
    """ISO週番号から週開始日(月曜)を求める。"""
    return datetime.fromisocalendar(year, week_number, 1)
