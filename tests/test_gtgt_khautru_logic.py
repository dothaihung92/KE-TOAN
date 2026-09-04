import sys

def simulate(tk_da_co, glv_da_co, preview=False):
    created = {"declaration": False, "voucher": False}
    if tk_da_co and glv_da_co:
        return {"trang_thai": "bo_qua", "created": created}

    # mirror the amount-source decision
    if not tk_da_co:
        amount_source = "computed_fresh"
    else:
        amount_source = "read_existing_declaration"

    if not tk_da_co:
        created["declaration"] = True
    if not glv_da_co:
        created["voucher"] = True

    if not tk_da_co and not glv_da_co:
        trang_thai = "se_tao" if preview else "da_tao"
    elif tk_da_co and not glv_da_co:
        trang_thai = "se_tao_but_toan_rieng" if preview else "da_tao_but_toan_rieng"
    else:
        trang_thai = "se_tao_to_khai_rieng" if preview else "da_tao_to_khai_rieng"

    return {"trang_thai": trang_thai, "created": created, "amount_source": amount_source}

cases = [
    # (tk_da_co, glv_da_co, expected_created_decl, expected_created_voucher, expected_amount_source)
    (False, False, True, True, "computed_fresh"),
    (True, False, False, True, "read_existing_declaration"),
    (False, True, True, False, "computed_fresh"),
    (True, True, False, False, None),  # skipped entirely
]

ok = True
for tk_da_co, glv_da_co, exp_decl, exp_vch, exp_src in cases:
    r = simulate(tk_da_co, glv_da_co, preview=False)
    label = f"tk_da_co={tk_da_co} glv_da_co={glv_da_co}"
    if tk_da_co and glv_da_co:
        passed = r["trang_thai"] == "bo_qua" and not r["created"]["declaration"] and not r["created"]["voucher"]
    else:
        passed = (r["created"]["declaration"] == exp_decl and
                  r["created"]["voucher"] == exp_vch and
                  r.get("amount_source") == exp_src)
    print(label, "->", r, "PASS" if passed else "FAIL")
    ok = ok and passed

# The specific user-reported scenario: declaration exists for all 4 quarters, voucher missing for all.
print()
print("User scenario: 4 quarters, declaration exists but voucher does not, for each:")
for i in range(4):
    r = simulate(True, False, preview=False)
    assert r["created"]["voucher"] is True and r["created"]["declaration"] is False
    print(f"  Quy {i+1}: voucher will be created (declaration left untouched) ->", r["trang_thai"])

print()
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
