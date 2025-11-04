from typing import List
import string  # ✅ برای حذف علائم نگارشی بدون دردسر کوتیشن‌ها

POSITIVE = {
    "optimism","optimistic","bull","bullish","rally","gain","up","surge","approve",
    "improve","positive","growth","strong","breakout","support","recover","rise",
    "green","beat","record","jump","strengthens","celebrate","recovery","momentum"
}

NEGATIVE = {
    "bear","bearish","fall","drop","down","sell","fear","panic","worry","risk-off",
    "recession","weak","loss","dump","crash","red","reject","bad","concern","slip",
    "correction","pressure"
}

def score_text(text: str) -> float:
    if not text:
        return 0.0
    # ✅ بدون کوتیشن‌های دردسرساز: همه‌ی علائم نگارشی استاندارد
    words = {w.strip(string.punctuation).lower() for w in text.split()}
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    if pos == 0 and neg == 0:
        return 0.0
    return (pos - neg) / max(1, pos + neg)

def score_texts(texts: List[str]) -> List[float]:
    return [score_text(t) for t in texts]
