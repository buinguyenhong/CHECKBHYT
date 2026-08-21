import datetime

def parse_date_info(date_val):
    if not date_val:
        d_obj = datetime.date.today()
    elif isinstance(date_val, (datetime.date, datetime.datetime)):
        d_obj = date_val if isinstance(date_val, datetime.date) else date_val.date()
    else:
        clean = str(date_val).strip().replace('-', '/').replace('.', '/')
        d_obj = None
        for fmt in ["%Y/%m/%d", "%d/%m/%Y", "%Y%m%d"]:
            try:
                d_obj = datetime.datetime.strptime(clean, fmt).date()
                break
            except Exception:
                pass
        if not d_obj:
            d_obj = datetime.date.today()
            
    return {
        "year": d_obj.year,
        "month": d_obj.month,
        "day": d_obj.day,
        "d_str": d_obj.strftime("%d/%m/%Y"),
        "iso": d_obj.strftime("%Y-%m-%d")
    }

print("2026-08-01 ->", parse_date_info("2026-08-01"))
print("2026-08-18 ->", parse_date_info("2026-08-18"))
print("01/08/2026 ->", parse_date_info("01/08/2026"))
