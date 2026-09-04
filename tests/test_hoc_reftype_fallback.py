import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i+1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln); continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i+1] + '\n'.join(body)


class FakeCursor:
    """Mô phỏng CSDL MISA công ty MỚI: bảng SUAllocation TỒN TẠI nhưng CHƯA CÓ
    dòng nào (chưa từng phân bổ CCDC) -> WHERE RefType<>0 rỗng -> phải rơi vào
    nhánh dò SYSRefType (dữ liệu hệ thống MISA có sẵn, không phụ thuộc công ty
    đã phát sinh chứng từ hay chưa)."""
    def __init__(self):
        self.sys_ref_type = [
            (4501, "Phân bổ chi phí công cụ dụng cụ"),
        ]

    def execute(self, sql, params=()):
        if "WHERE RefType<>0" in sql and "SUAllocation" in sql:
            self._result = []   # công ty MỚI - chưa có dòng nào
        elif "SYSRefType WHERE MasterTableName" in sql:
            self._result = self.sys_ref_type
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


ns = {}
exec(extract_fn('_misa_pu_reftype'), ns)
exec(extract_fn('_misa_hoc_reftype'), ns)
_misa_hoc_reftype = ns['_misa_hoc_reftype']

cur = FakeCursor()

# Trước fix: hàm gọi ngoài (_misa_phan_bo_ccdc) sẽ raise HTTPException ngay nếu
# CHƯA có chứng từ PBCC thật nào. Sau fix: phải tự dò được RefType qua
# SYSRefType (KHÔNG cần chứng từ mẫu) -> trả về (4501, None) chứ KHÔNG (None, None).
rt, dob = _misa_hoc_reftype(cur, "SUAllocation", "phân bổ")
assert rt == 4501, f"Phải tự dò được RefType=4501 qua SYSRefType, không cần chứng từ mẫu — got {rt}"
assert dob is None, "SYSRefType không có cột DisplayOnBook -> None (chỗ gọi sẽ tự default 0)"
print("PASS: _misa_hoc_reftype tự dò được RefType qua SYSRefType khi bảng CHƯA có dòng nào "
      "(công ty mới, chưa từng tạo chứng từ Phân bổ chi phí CCDC tay) — không còn phụ thuộc "
      "phải có sẵn ít nhất 1 chứng từ mẫu.")

print("\nALL DONE")
