import os, sys, types, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpkd_soan as g

# Ca thật (Windows, có Word): xuất PDF báo "(-2147221008, 'CoInitialize has not been called.')" vì hàm chạy trong luồng của máy chủ web mà chưa
# khởi tạo COM. Nay khởi tạo COM cho luồng trước khi mở Word và giải phóng sau đó (kể cả khi lỗi). Kiểm tra bằng thư viện giả.
LOG = []


def dung(mod_name):
    com = types.ModuleType("pythoncom")
    com.CoInitialize = lambda: LOG.append("init")
    com.CoUninitialize = lambda: LOG.append("uninit")

    class Doc:
        def SaveAs(self, out, FileFormat=None):
            LOG.append("save"); open(out, "wb").write(b"%PDF-fake")
        def Close(self, x): LOG.append("close")

    class Word:
        Visible = True
        class Documents:
            @staticmethod
            def Open(src, ReadOnly=True):
                LOG.append("open"); return Doc()
        def Quit(self): LOG.append("quit")
    wc = types.ModuleType("win32com.client")
    wc.DispatchEx = lambda n: (LOG.append("dispatch") or Word())
    pk = types.ModuleType("win32com"); pk.client = wc
    sys.modules.update({"pythoncom": com, "win32com": pk, "win32com.client": wc})


dung("win32com")
kq = []
t = threading.Thread(target=lambda: kq.append(g.docx_sang_pdf(b"x", ("word", "win32com.client"))))
t.start(); t.join()
assert kq == [b"%PDF-fake"], kq
assert LOG[0] == "init" and LOG.index("dispatch") > 0 and LOG[-1] == "uninit" and LOG.index("quit") < LOG.index("uninit"), LOG
print("PASS 1: khởi tạo COM trước khi mở Word, giải phóng sau khi thoát Word.")

LOG.clear()
sys.modules["win32com.client"].DispatchEx = lambda n: (_ for _ in ()).throw(RuntimeError("Word lỗi"))
try:
    g.docx_sang_pdf(b"x", ("word", "win32com.client"))
    assert False
except RuntimeError:
    pass
assert LOG == ["init", "uninit"], LOG
print("ALL DONE")
