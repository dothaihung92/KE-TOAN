import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Hộp thoại PIN bản tiếng Anh của token ("PIN Verification": "Now need verify your User PIN:", ô "PIN code:", nút Change PIN / Login / Cancel,
# ô "Enable soft keyboard") phải được nhận ra và tự nhập PIN như các hộp thoại tiếng Việt; vẫn giữ giới hạn an toàn: tối đa 2 lần, sai thì bấm Cancel.
class Ctl:
    def __init__(self, text="", kieu="Text", dlg=None): self.text = text; self.kieu = kieu; self.dlg = dlg; self.da_nhap = None
    def window_text(self): return self.text
    def set_focus(self): pass
    def set_edit_text(self, t): pass
    def type_keys(self, pin, with_spaces=True): self.dlg.pin_nhap.append(pin)
    def click_input(self): self.dlg.bam.append(self.text)

class Dlg:
    def __init__(self, tieu_de, dung_pin, edit=True):
        self.tieu_de = tieu_de; self.dung_pin = dung_pin; self.pin_nhap = []; self.bam = []; self.dong = False
        self.cs = [Ctl("Now need verify your User PIN:", "Text", self), Ctl("PIN code:", "Text", self)]
        if edit: self.cs.append(Ctl("", "Edit", self))
        self.cs += [Ctl("Enable soft keyboard", "CheckBox", self), Ctl("Change PIN", "Button", self), Ctl("Login", "Button", self), Ctl("Cancel", "Button", self)]
    def window_text(self): return self.tieu_de
    def is_visible(self): return not self.dong
    def descendants(self, control_type=None): return [c for c in self.cs if c.kieu == control_type]

class MoPhong:
    """Mô phỏng: bấm Login -> nếu PIN nhập đúng thì hộp thoại đóng; bấm Cancel -> đóng."""
    def __init__(self, dlg, wins=()): self.dlg = dlg; self.wins = list(wins)
    def windows(self):
        if self.dlg.bam and self.dlg.bam[-1] == "Login" and self.dlg.pin_nhap and self.dlg.pin_nhap[-1] == self.dlg.dung_pin: self.dlg.dong = True
        if self.dlg.bam and self.dlg.bam[-1] == "Cancel": self.dlg.dong = True
        return [self.dlg] + self.wins

def chay(dlg, pin, wins=()):
    mp = MoPhong(dlg, wins)
    fake = types.ModuleType("pywinauto"); fake.Desktop = lambda backend=None: mp
    sys.modules["pywinauto"] = fake
    import time as _t
    goc = server.time.sleep if hasattr(server, "time") else None
    return server._dvc_nhap_pin_ky_so(pin, cho_hien_toi_da=2, cho_dong_toi_da=1)

assert "PIN Verification" in server._DVC_PIN_DIALOG_TITLES
assert server._dvc_la_hop_thoai_pin(Dlg("PIN Verification", "1")) is True
assert server._dvc_la_hop_thoai_pin(Dlg("PIN Verification", "1", edit=False)) is False, "không có ô nhập -> không phải hộp thoại PIN"
assert server._dvc_la_hop_thoai_pin(Dlg("Another Window", "1")) is False
print("PASS 1: nhận ra hộp thoại 'PIN Verification' (có ô nhập + nhắc PIN); cửa sổ khác tên/không có ô nhập thì bỏ qua.")

# 2) đúng PIN -> nhập, bấm Login, hộp thoại đóng
d = Dlg("PIN Verification", "12345678")
kq = chay(d, "12345678")
assert kq["ok"] and kq["so_lan_da_thu"] == 1, kq
assert d.pin_nhap == ["12345678"] and d.bam == ["Login"], (d.pin_nhap, d.bam)
print("PASS 2: tự nhập PIN vào ô 'PIN code' và bấm 'Login' (không bấm Change PIN/Cancel) -> hộp thoại đóng, thành công.")

# 3) sai PIN: chỉ 2 lần rồi bấm Cancel, không bao giờ lần thứ 3
d = Dlg("PIN Verification", "dung-pin")
kq = chay(d, "sai-pin")
assert not kq["ok"] and kq.get("sai_pin") and kq["so_lan_da_thu"] == 2, kq
assert d.pin_nhap == ["sai-pin", "sai-pin"] and d.bam == ["Login", "Login", "Cancel"], (d.pin_nhap, d.bam)
print("PASS 3: sai PIN -> thử tối đa 2 lần rồi bấm 'Cancel' (tránh khoá token), không thử lần 3.")

# 4) số lần còn lại bằng tiếng Anh
d = Dlg("PIN Verification", "1"); d.cs.insert(0, Ctl("3 attempts left", "Text", d))
assert server._dvc_so_lan_con_lai(d) == 3
d2 = Dlg("PIN Verification", "dung"); d2.cs.insert(0, Ctl("2 attempts left", "Text", d2))
kq = chay(d2, "x")                    # còn 2 lần -> chỉ được thử 1 lần (luôn chừa lại 1 lần cho người dùng), sai thì Cancel
assert d2.pin_nhap == ["x"] and d2.bam == ["Login", "Cancel"] and kq["sai_pin"], (d2.pin_nhap, d2.bam, kq)
d3 = Dlg("PIN Verification", "dung"); d3.cs.insert(0, Ctl("1 attempt left", "Text", d3))
kq = chay(d3, "dung")                 # còn 1 lần -> KHÔNG tự thử
assert d3.pin_nhap == [] and d3.bam == [] and not kq["ok"] and kq["so_lan_da_thu"] == 0
print("PASS 4: đọc số lần còn lại bằng tiếng Anh ('N attempts left'): luôn chừa lại ít nhất 1 lần, còn 1 lần thì không tự thử.")
print("ALL DONE")
