# Mô phỏng tra cứu hàng loạt với captcha (xem kết luận ở cuối file)
import sys, threading, time, json, re
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
server.time.sleep = (lambda f: (lambda s: f(min(s, 0.02))))(time.sleep)
class R:
    def __init__(s,c,b): s.status_code=c; s._b=b; s.headers={}
    @property
    def text(s): return json.dumps(s._b)
    def json(s): return s._b
    def raise_for_status(s):
        if s.status_code>=400: raise Exception(s.status_code)
class S:
    def __init__(s): s.da=set(); s.l=threading.Lock(); s.urls=[]; s.headers={}
    def get(s,url,headers=None,timeout=None,params=None):
        with s.l: s.urls.append(url)
        if url.endswith('/captcha'): return R(200,{"key":"K","content":"<svg/>"})
        m=re.search(r"cvalue=([A-Z0-9]+)",url)
        with s.l:
            if m and m.group(1) not in s.da:
                s.da.add(m.group(1))
                n=len(s.da)
                return R(200,{"datas":[{"shdon":url,"khhdon":"K","khmshdon":1,"nbmst":"1"}],"total":1,"state":None})
        return R(429,{"e":"Too Many Requests"})
    def close(s): pass
def tao(cid):
    c=server.GDTClient.__new__(server.GDTClient); c.session=S(); c.token="T"; c.impersonate=False
    c._ban_sao_phien_moi=lambda c=c:c
    c._trang_thai_captcha()
    n=[0]
    c.captcha_cb=lambda cancel_check=None:(n.__setitem__(0,n[0]+1) or ("k","M%d%d"%(cid,n[0])))
    c._hoi=n
    return c
server._solve_captcha=lambda *a,**k:""
res={}
def chay(cid,loai,ht):
    c=tao(cid)
    lim=server.DynamicLimiter(1)
    t0=time.time()
    r,tot,loi,doan=c.query_invoices("01/09/2026","30/09/2026",loai=loai,he_thong=ht,mtt_limiter=lim)
    res[(cid,loai,ht)]=(len(r),tot,len(loi),len(doan),c._hoi[0],round(time.time()-t0,1))
ths=[threading.Thread(target=chay,args=(cid,loai,ht)) for cid in (1,2,3) for loai,ht in (("sold","sco-query"),("purchase","sco-query"),("sold","query"))]
for t in ths: t.start()
for t in ths: t.join(120)
# Tra cứu HÀNG LOẠT: mỗi công ty 1 luồng (limiter=1), 3 công ty chạy song song, mua vào/bán ra × thường/MTT, mỗi mã captcha CHỈ dùng 1 lượt
# (trường hợp xấu nhất) -> mọi công ty/loại đều lấy ĐỦ hóa đơn (tổng lấy được = tổng trang Thuế báo), không công ty nào bị bỏ đói.
assert len(res) == len(ths) == 9, res
for k, (so_hd, tong, so_loi, so_doan_loi, so_hoi, _giay) in res.items():
    assert so_hd == tong and so_loi == 0 and so_doan_loi == 0 and so_hoi >= 1, (k, res[k])
print("PASS: tra cứu hàng loạt (3 công ty song song, mỗi công ty 1 luồng) lấy đủ hóa đơn cả 3 loại dù mỗi mã captcha chỉ dùng 1 lượt.")
print("ALL DONE")
