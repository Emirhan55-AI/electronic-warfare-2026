from scripts.verify_st06_parallel_product import verify

def test_parallel_product_evidence_and_separate_rf_gate():
    result=verify()
    assert result['gates']['digital_product_throughput']
    assert not result['gates']['ST06_complete']
