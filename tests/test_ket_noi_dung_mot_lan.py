import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Yêu cầu: kết nối đã dùng tải 1 lần thì không quay lại kết nối đó để tải nữa (kết nối cũ nằm im bị Thuế đóng ngầm -> "Remote end closed").
# Mỗi lượt tải file / lấy chi tiết hóa đơn dùng 1 kết nối MỚI rồi ĐÓNG HẲN; phiên chính (self.session) không bị dùng để tải.
tao, dong = [], []
class Resp:
    status_code = 200
    content = b"PK\x03\x04zipdata"
    headers = {}
    def json(self): return {"shdon": "1"}
class Phien:
    def __init__(self, ten): self.ten = ten; self.headers = {}; self.cookies = {}; self.n = 0
    def get(self, *a, **k): self.n += 1; return Resp()
    def close(self): dong.append(self.ten)
class Chinh(Phien):
    def get(self, *a, **k): raise AssertionError("không được dùng phiên chính để tải")
c = server.GDTClient.__new__(server.GDTClient)
c.impersonate = False; c._http11 = False; c.token = "T"
c.session = Chinh("chinh"); c.session.headers = {"Authorization": "Bearer T"}; c.session.cookies = {"TS01": "x"}
goc = server.requests.Session
def moi():
    p = Phien(f"mot-lan-{len(tao)}"); tao.append(p); return p
server.requests.Session = moi
try:
    for i in range(5):
        assert c.download_xml("0100", "C26TAA", 1, str(i)) == Resp.content
    assert c.get_detail("0100", "C26TAA", 1, "1") == {"shdon": "1"}
finally:
    server.requests.Session = goc
assert len(tao) == 6 and len(set(id(p) for p in tao)) == 6, "mỗi lượt 1 kết nối mới"
assert all(p.n == 1 for p in tao), "mỗi kết nối chỉ dùng đúng 1 lần"
assert dong == [p.ten for p in tao], "tải xong là đóng hẳn"
assert all(p.headers.get("Authorization") == "Bearer T" and p.cookies.get("TS01") == "x" for p in tao), "giữ đăng nhập/cookie"
print("PASS 1: 5 lượt tải file + 1 lượt chi tiết = 6 kết nối mới, mỗi kết nối dùng 1 lần rồi đóng, không dùng lại phiên chính.")

# lỗi mạng ở lượt 1 -> lượt thử lại cũng dùng kết nối MỚI
tao.clear(); dong.clear()
class PhienLoi(Phien):
    def get(self, *a, **k): self.n += 1; raise ConnectionError("Connection aborted")
lan = [0]
def moi2():
    lan[0] += 1
    p = (PhienLoi if lan[0] == 1 else Phien)(f"p{lan[0]}"); tao.append(p); return p
server.requests.Session = moi2
server.time.sleep = lambda s: None
try:
    assert c.download_xml("0100", "C26TAA", 1, "9") == Resp.content
finally:
    server.requests.Session = goc
assert len(tao) == 2 and dong == ["p1", "p2"]
print("PASS 2: lượt tải bị ngắt -> lượt thử lại dùng kết nối MỚI (không quay lại kết nối đã hỏng); cả hai đều được đóng.")
print("ALL DONE")
