from pathlib import Path

from lakehouse.ingestion.validator import validate_csv

ROOT = Path(__file__).resolve().parents[1]


def test_valid_sample(specs):
    r = validate_csv(ROOT / "data/onprem/orders/orders_20261027.csv", specs["orders"])
    assert r.ok and r.row_count == 6


def test_header_mismatch(tmp_path, specs):
    f = tmp_path / "bad.csv"
    f.write_text("a,b\n1,2\n")
    r = validate_csv(f, specs["customers"])
    assert not r.ok and "header mismatch" in r.errors[0]


def test_null_pk_rejected(tmp_path, specs):
    f = tmp_path / "pk.csv"
    f.write_text("product_id,sku,product_name,category,unit_price,active,updated_at\n,X,Y,Z,1,true,2026-01-01\n")
    r = validate_csv(f, specs["products"])
    assert not r.ok and "null primary key" in r.errors[0]
