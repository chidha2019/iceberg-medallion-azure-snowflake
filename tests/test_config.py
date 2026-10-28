def test_contracts_load_with_defaults(specs):
    assert set(specs) == {"customers", "products", "orders"}
    assert specs["orders"].primary_key == ["order_id", "line_number"]
    assert specs["orders"].blob_prefix == "landing"  # inherited default
    assert specs["customers"].bronze_table == "BRONZE.CUSTOMERS"
