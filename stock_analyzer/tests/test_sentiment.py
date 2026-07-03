from stock_analyzer.analysis.sentiment import aggregate_sentiment, score_headline


def test_positive_headline():
    s = score_headline("Doanh nghiệp báo lãi lớn, lợi nhuận tăng vọt trong quý")
    assert s.score > 0


def test_negative_headline():
    s = score_headline("Cổ phiếu giảm sàn, nhà đầu tư bán tháo vì lo ngại nợ xấu")
    assert s.score < 0


def test_neutral_headline():
    s = score_headline("Công ty tổ chức đại hội cổ đông thường niên")
    assert s.score == 0.0


def test_aggregate_sentiment_mixed():
    headlines = [
        "Lợi nhuận tăng trưởng mạnh, vượt kế hoạch năm",
        "Cổ phiếu lao dốc sau tin đồn thanh tra",
        "Đại hội cổ đông diễn ra bình thường",
    ]
    score = aggregate_sentiment(headlines)
    assert -1.0 <= score <= 1.0


def test_aggregate_sentiment_empty():
    assert aggregate_sentiment([]) == 0.0
