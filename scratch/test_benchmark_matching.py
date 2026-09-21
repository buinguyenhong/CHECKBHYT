import time
import re

class MockRecord:
    def __init__(self, i):
        self.id = i
        self.ma_lk = f"LK{i:06d}"
        self.maloi = "XML3" if i % 2 == 0 else "XML5"
        self.motaloi = "DIEN_BIEN_LS bi thieu o dong chi tiet" if i % 2 == 0 else "NGAY_TH_YL sai"

class MockDef:
    def __init__(self, code, kw):
        self.error_code = code
        self.keyword = kw
        self.root_cause = f"Nguyen nhan {code} {kw}"
        self.resolution = f"Xu ly {code} {kw}"
        self.requires_his_reset = False

# 65 standard definitions
defs = [
    MockDef(f"XML{i}", kw) 
    for i in range(1, 14) 
    for kw in ["DIEN_BIEN_LS", "TOMTAT_KQ", "MA_BS_DOC_KQ", "KET_LUAN", "MA_BAC_SI"]
]

records = [MockRecord(i) for i in range(10000)]

print(f"Testing with {len(records)} records and {len(defs)} error definitions...")

# 1. Old Nested Loop Benchmark
t0 = time.perf_counter()
old_results = []
for r in records:
    r_clean = re.sub(r'[^A-Z0-9]', '', str(r.maloi or "").upper())
    for d in defs:
        d_clean = re.sub(r'[^A-Z0-9]', '', str(d.error_code).upper())
        if d_clean == r_clean:
            if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                old_results.append((r.id, d.error_code))
                break
t_old = time.perf_counter() - t0
print(f"Old nested loop time: {t_old:.4f} seconds ({len(old_results)} matched)")

# 2. New Optimized O(1) Dictionary Benchmark
t1 = time.perf_counter()
defs_by_code = {}
for d in defs:
    d_clean = re.sub(r'[^A-Z0-9]', '', str(d.error_code or "").upper())
    if d_clean:
        if d_clean not in defs_by_code:
            defs_by_code[d_clean] = []
        defs_by_code[d_clean].append(d)

new_results = []
for r in records:
    r_clean = re.sub(r'[^A-Z0-9]', '', str(r.maloi or "").upper())
    matched_defs = defs_by_code.get(r_clean)
    if matched_defs:
        for d in matched_defs:
            if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                new_results.append((r.id, d.error_code))
                break
t_new = time.perf_counter() - t1
print(f"New dictionary time:  {t_new:.4f} seconds ({len(new_results)} matched)")
print(f"Speedup: {t_old / t_new:.2f}x faster!")
assert old_results == new_results, "Results mismatch!"
print("PASS: Logic and results are 100% identical!")
