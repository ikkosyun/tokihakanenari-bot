"""投稿キャプション（本文）と、残り日数・残り%の計算。

計算方式は参考にしたXの「今年の残り日数」botに合わせている:
  経過日数 = 年間通算日 - 1  (今日はまだ「終わっていない日」として数えない)
  残り日数 = 年間日数 - 経過日数
  残り%   = 残り日数 / 年間日数 * 100
"""
from dataclasses import dataclass
from datetime import date

from season import SeasonTheme


@dataclass(frozen=True)
class DayStats:
    year: int
    month: int
    day: int
    total_days: int
    remaining_days: int
    remaining_percent: float


def compute_day_stats(target_date: date) -> DayStats:
    total_days = 366 if _is_leap(target_date.year) else 365
    day_of_year = target_date.timetuple().tm_yday
    elapsed_days = day_of_year - 1
    remaining_days = total_days - elapsed_days
    remaining_percent = remaining_days / total_days * 100
    return DayStats(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        total_days=total_days,
        remaining_days=remaining_days,
        remaining_percent=remaining_percent,
    )


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def build_header(stats: DayStats) -> str:
    date_line = f"{stats.year}年{stats.month}月{stats.day}日になりました。"
    remain_line = f"今年は残り{stats.remaining_days}日です。あと{stats.remaining_percent:.1f}%です。"
    return f"{date_line}\n{remain_line}"


def build_caption(stats: DayStats, theme: SeasonTheme, story: str) -> str:
    return (
        f"{build_header(stats)}\n"
        f"\n"
        f"{story}\n"
        f"\n"
        f"#今年の残り日数 #時間の大切さ #{theme.label.replace('・', '')}"
    )
