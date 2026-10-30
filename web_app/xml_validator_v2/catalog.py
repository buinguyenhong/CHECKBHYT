# Danh mục 123 quy tắc kiểm tra XML:
# 1. 116 quy tắc logic trích xuất từ:
#    - GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx (9324, 4210)
#    - TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx (4750)
# 2. 7 nhóm quy tắc bổ sung từ QD4750_Check_Validate CTN QĐ_4750.xlsx (CTN_*)

RULE_CATALOG = [
    {
        "standard": "9324",
        "rule_code": "1",
        "rule_name": "Mã lỗi 1: Sai lý do vào viện",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nMã lý do vào viện đề nghị khác các giá trị (1, 2, 3, 4)\nMã lý do vào viện đề nghị =3 nhưng Mã ĐKBĐ = Mã CSKCB (Đúng tuyến mà gửi lên là trái tuyến).",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "3",
        "rule_name": "Mã lỗi 3: Sai thành tiền so với SO_LUONG, DON_GIA của XML2 và XML3",
        "description": "XML2, XML3 vi phạm khi THANH_TIEN khác (SO_LUONG * DON_GIA * TYLE/100)",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "4",
        "rule_name": "Mã lỗi 4: Sai TONG_CHI của XML1 so với THANH_TIEN của XML2 và XML3.",
        "description": "Hồ sơ vi phạm khi T_TONGCHI khác tổng (THANH_TIEN) của các xml2, xml3.",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "5",
        "rule_name": "Mã lỗi 5: Sai TONG_CHI so với T_BHTT và T_BNTT của XML1.",
        "description": "Hồ sơ vi phạm khi: T_TONGCHI khác tổng T_BNTT + T_BHTT + T_NGUONKHAC (cho phép lệch 1 đơn vị).",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "8",
        "rule_name": "Mã lỗi 8: Sai thông tin thẻ",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nTrong danh mục mức hưởng BHYT, không tìm thấy bản ghi có hiệu lực và có mã = 3 ký tự đầu thẻ BHYT\nTrong danh mục đơn vị BHXH, không tim thấy bản ghi có mã đơn vị = 2 ký tự thứ 4, 5 của mã thẻ BHYT.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "9",
        "rule_name": "Mã lỗi 9 (Sai thông tin CSKCB ban đầu)",
        "description": "Bỏ qua với trường hợp trẻ em không thẻ (2 ký tự đầu mã thẻ là TE; 3 ký tự thứ 8,9,10 là ‘000’ và Mã ĐKBĐ = mã đơn vị +’000’), nếu hồ sơ có Mã ĐKBĐ không nằm trong danh mục Cơ sở KCB thì vi phạm.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "10",
        "rule_name": "Mã lỗi 10 (Sai thông tin CSKCB)",
        "description": "Hồ sơ vi phạm mã lỗi trên khi: mã CSKCB của hồ sơ không tìm thấy trong danh mục CSKCB.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "11",
        "rule_name": "Mã lỗi 11 (Hồ sơ không phát sinh chi phí Đề nghị thanh toán)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nHồ sơ có tiền đề nghị BHTT trống hoặc = 0\nHồ sơ có mức hưởng đề nghị trống hoặc = 0",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "12",
        "rule_name": "Mã lỗi 12: Sai T_BHTT tính lại từ mức hưởng (BỎ QUA VỚI TH HỒ SƠ CÓ GOI_VTYT)",
        "description": "Tính lại T_BHTT chi tiết của các XML2, XML3 theo công thức sau:\nXML2: T_BHTT = so_luong * don_gia * tyle/100 * muc_huong/100\nXML3:\nMã nhóm 12: T_BHTT = so_luong * don_gia * tyle/100\nMã nhóm 10, 11 nằm trong gói:\nT_BHTT = so_luong * don_gia * tyle/100 * muc_huong/100 * tỷ lệ áp trần\nCác mã nhóm còn lại: T_BHTT = so_luong * don_gia * tyle/100 * muc_huong/100\nThực hiện so sánh: T_BHTT đề nghị tại XML1 với tổng T_BHTT vừa tính lại của các XML2, XML3. Nếu khác nhau thì hồ sơ vi phạm.",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "14",
        "rule_name": "Mã lỗi 14 (Stent động mạch vành phủ thuốc các cỡ các loại thanh toán theo TT 04/2017/TT-BYT)",
        "description": "Hồ sơ vi phạm mã lỗi trên khi: đề nghị chi phí VTYT STENT mã “N06.02.020’ với số lượng > 1\n(bỏ qua xét mã lỗi này với các hồ sơ có mã thẻ là CC, TE, QN, CA, CY hoặc hồ sơ có ngày ra trước ngày 01/01/2017)",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "60",
        "rule_name": "Mã lỗi 60 (Cơ sở đăng ký khám ngoại trú nhận hồ sơ nội trú không hợp lệ)",
        "description": "Hồ sơ vi phạm nếu thỏa mãn tất cả các điều kiện sau:\nMã loại KCB = 3 (nội trú)\nCơ sở KCB đăng ký khám Ngoại trú\n(Trong bảng LOG_LOAIHOPDONG của cơ sở đó thỏa mãn: LOAI_HOPDONG = 0 và NGAY_VAO của hồ sơ nằm trong khoảng TU_NGAY, DEN_NGAY.\nTrường hợp trong bảng LOG_LOAIHOPDONG ko có bản ghi thỏa mãn thì tìm cơ sở kcb đó trong Danh mục cơ sở KCB, cơ sở có LOAI_HOPDONG = 0).",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "9324",
        "rule_code": "61",
        "rule_name": "Mã lỗi 61: Trùng hồ sơ",
        "description": "Phần này thực hiện đầu tiên trước khi làm các tác vụ khác, bộ key trùng: mã thẻ, họ tên, ngày vào, ngày ra, mã bệnh, mã cơ sở kcb, kỳ quyết toán, T_TONGCHI, T_BHTT.\nNếu tồn tại 1 bản ghi đã có tại giám định với cả 2 tiền T_TONGCHI và T_BHTT lệch nhau không quá 2 đồng thì trả về hồ sơ.\nHồ sơ gửi theo 4210",
        "category": "CROSS_RECORD_DUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "1",
        "rule_name": "Mã lỗi 1: Sai lý do vào viện",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nMã lý do vào viện đề nghị khác các giá trị (1, 2, 3, 4)\nMã lý do vào viện đề nghị =3 nhưng Mã ĐKBĐ = Mã CSKCB (Đúng tuyến mà gửi lên là trái tuyến).",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "8",
        "rule_name": "Mã lỗi 8: Sai thông tin thẻ",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nTrong danh mục mức hưởng BHYT, không tìm thấy bản ghi có hiệu lực và có mã = 3 ký tự đầu thẻ BHYT\nTrong danh mục đơn vị BHXH, không tim thấy bản ghi có mã đơn vị = 2 ký tự thứ 4, 5 của mã thẻ BHYT.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "9",
        "rule_name": "Mã lỗi 9 (Sai thông tin CSKCB ban đầu)",
        "description": "Với các hồ sơ thỏa mãn tất cả các điều kiện sau sẽ bỏ qua không xét mã lỗi này:\n3 ký tự đầu của mã thẻ có trong danh mục mức hưởng BHYT, và có hiệu lực\n2 ký tự thứ 4, 5 của mã thẻ có trong danh mục đơn vị BHYT\n2 ký tự thứ 6, 7 của mã thẻ là “KT”\n3 ký tự đầu mã thẻ là TE1, HG4 và QTTHE = 700000 và mã đk ban đầu có định dạng XX000 trong đó XX = =DM_TINHTHANH.MA\nCác hồ sơ không thuộc trường hợp trên thì xét tiếp, nếu vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nKhông tìm thấy mã ĐKBĐ của hồ sơ trong danh mục Cơ sở kcb.\nHồ sơ có Mã ĐKBĐ khác, nhưng dữ liệu ở trường này: các mã CSKCB không cách nhau bởi dấu “;”\nHồ sơ có Mã ĐKBĐ khác, dữ liệu ở trường này: các mã CSKCB cách nhau bởi dấu “;”.\nNhưng trong số các mã CSKCB đó, tồn tại ít nhất 1 mã CSKCB không có trong danh mục CSKCB.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "10",
        "rule_name": "Mã lỗi 10 (Sai thông tin CSKCB)",
        "description": "Hồ sơ vi phạm mã lỗi trên khi: mã CSKCB của hồ sơ không tìm thấy trong danh mục CSKCB.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "11",
        "rule_name": "Mã lỗi 11 (Hồ sơ không phát sinh chi phí Đề nghị thanh toán)",
        "description": "Hồ sơ vi phạm trường hợp sau sẽ bị trả về mã lỗi trên: tiền đề nghị BHTT trống hoặc =0",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "14",
        "rule_name": "Mã lỗi 14 (Stent động mạch vành phủ thuốc các cỡ các loại thanh toán theo TT 04/2017/TT-BYT)",
        "description": "Hồ sơ vi phạm mã lỗi trên khi: đề nghị chi phí VTYT STENT mã “N06.02.020’ với số lượng > 1\n(bỏ qua xét mã lỗi này với các hồ sơ có mã thẻ là CC, TE, QN, CA, CY hoặc hồ sơ có ngày ra trước ngày 01/01/2017)",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "15",
        "rule_name": "Mã lỗi 15 (Ngày sinh không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường ngày sinh không đúng 8 ký tự số\nGiá trị trường ngày sinh không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "16",
        "rule_name": "Mã lỗi 16 (giới tính không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị giới tính đề nghị lên khác (1,2,3)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "17",
        "rule_name": "Mã lỗi 17 (Mã thẻ không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Mã thẻ không đúng 15 ký tự\nGiá trị trường Mã thẻ khác không null, nhưng các mã thẻ trong trường mã thẻ khác không cách nhau bởi dấu “;”\nGiá trị trường Mã thẻ khác không null, các mã thẻ trong trường mã thẻ khác cách nhau bởi dấu “;”. Nhưng trong đó tồn tại 1 giá trị mã thẻ không đúng 15 ký tự.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "18",
        "rule_name": "Mã lỗi 18 (giá trị thẻ từ không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường giá trị thẻ từ khác không null, nhưng các giá trị trong trường này không cách nhau bởi dấu “;”\nGiá trị trường giá trị thẻ từ khác không null, các giá trị trong trường này cách nhau bởi dấu “;”, nhưng trong đó tồn tại 1 giá trị không đúng 8 ký tự số.\nGiá trị trường giá trị thẻ từ khác không null, các giá trị trong trường này cách nhau bởi dấu “;”,nhưng trong đó tồn tại 1 giá trị không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "19",
        "rule_name": "Mã lỗi 19 (giá trị thẻ đến không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường giá trị thẻ đến khác không null, nhưng các giá trị trong trường này không cách nhau bởi dấu “;”\nGiá trị trường giá trị thẻ đến khác không null, các giá trị trong trường này cách nhau bởi dấu “;”, nhưng trong đó tồn tại 1 giá trị không đúng 8 ký tự số.\nGiá trị trường giá trị thẻ đến khác không null, các giá trị trong trường này cách nhau bởi dấu “;”,nhưng trong đó tồn tại 1 giá trị không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "20",
        "rule_name": "Mã lỗi 20 (Số lượng mã thẻ và các thông tin thẻ không tương ứng)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nNếu trong 4 trường XML1.MA_THE_KHAC, XML1.MA_DKBD_KHAC, XML1.GT_THE_TU_KHAC, XML1.GT_THE_DEN_KHAC có trường rỗng, nhưng các trường còn lại vẫn có giá trị\nTách các giá trị trong 4 trường trên theo dấu “;”,thành danh sách các giá trị cụ thể. Nếu số lượng bốn danh sách tách được không bằng nhau (ví dụ 4 mã thẻ, 3 cơ sở ĐKBĐ, 5 giá trị từ, 5 giá trị đến)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "21",
        "rule_name": "Mã lỗi 21 (Miễn cùng chi trả không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Miễn cùng chi trả không đúng 8 ký tự số\nGiá trị trường Miễn cùng chi trả không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "22",
        "rule_name": "Mã lỗi 22 (Mã tai nạn không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường mã tại nạn không thuộc các giá trị từ 0 đến 8.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "23",
        "rule_name": "Mã lỗi 23 (Ngày vào không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Ngày vào không đúng 12 ký tự số\nGiá trị trường Ngày vào không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "24",
        "rule_name": "Mã lỗi 24 (Ngày ra không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Ngày ra không đúng 12 ký tự số\nGiá trị trường Ngày ra không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "25",
        "rule_name": "Mã lỗi 25 (Kết quả điều trị không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường Kết quả điều trị không thuộc các giá trị từ 1đến 5.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "26",
        "rule_name": "Mã lỗi 26 (Tình trạng ra viện không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường Tình trạng ra viện không thuộc các giá trị từ 1đến 4.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "27",
        "rule_name": "Mã lỗi 27 (Ngày thanh toán không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Ngày thanh toán không đúng 12 ký tự số\nGiá trị trường Ngày thanh toán không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "31",
        "rule_name": "Mã lỗi 31 (T_BHTT trong XML1 khác tổng cộng các T_BHTT trong XML23)",
        "description": "Hồ sơ vi phạm khi:\nT_BHTT trong xml1 != Tổng (T_BHTT) trong xml2 + Tổng (T_BHTT) trong xml3",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "34",
        "rule_name": "Mã lỗi 34 (TONGCHI trong XML1 khác tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC)",
        "description": "Hồ sơ vi phạm khi:\nTONGCHI trong XML1 != Tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "35",
        "rule_name": "Mã lỗi 35 (Năm quyết toán không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Năm quyết toán > Năm hiện tại.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "36",
        "rule_name": "Mã lỗi 36 (Tháng quyết toán không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Tháng quyết toán không thuộc các giá trị từ 1đến 12.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "37",
        "rule_name": "Mã lỗi 37 (Mã loại KCB không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Mã loại KCB không thuộc các giá trị từ 1đến 3.",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "38",
        "rule_name": "Mã lỗi 38 (Mã KHU VỰC không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Mã khu vực không thuộc các giá trị (K1, K2, K3)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "39",
        "rule_name": "Mã lỗi 39 (Mã nhóm trong XML2 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML2 có giá trị Mã nhóm khác (4, 5, 6, 7)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "40",
        "rule_name": "Mã lỗi 40 (Phạm vi trong XML2 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML2 có giá trị trường Phạm vi khác (1, 2)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "41",
        "rule_name": "Mã lỗi 41 (THANHTIEN trong XML2 khác tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC)",
        "description": "Hồ sơ vi phạm khi trong XML2 tồn tại ít nhất 1 bản ghi mà:\nTHANH_TIEN trong XML2 != Tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "42",
        "rule_name": "Mã lỗi 42 (T_NGOAIDS trong XML2 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML2 có giá trị trường T_NGOAIDS đề nghị khác 0 và khác giá trị trường T_BHTT.",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "43",
        "rule_name": "Mã lỗi 43 (Mã nhóm trong XML3 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML3 có giá trị Mã nhóm khác (1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "44",
        "rule_name": "Mã lỗi 44 (Phạm vi trong XML3 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML3 có giá trị trường Phạm vi khác (1, 2)",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "45",
        "rule_name": "Mã lỗi 45 (THANHTIEN trong XML3 khác tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC)",
        "description": "Hồ sơ vi phạm khi trong XML3 tồn tại ít nhất 1 bản ghi mà:\nTHANH_TIEN trong XML3 != Tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "46",
        "rule_name": "Mã lỗi 46 (T_NGOAIDS trong XML3 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML3 có giá trị trường T_NGOAIDS đề nghị khác 0 và khác giá trị trường T_BHTT.",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "47",
        "rule_name": "Mã lỗi 47: Thành tiền trong XML2 không hợp lệ",
        "description": "XML2 vi phạm khi THANH_TIEN khác (so_luong * don_gia)",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "48",
        "rule_name": "Mã lỗi 48: T_BHTT trong XML2 không hợp lệ",
        "description": "",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "49",
        "rule_name": "Mã lỗi 49: T_BNCCT trong XML2 không hợp lệ",
        "description": "",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "50",
        "rule_name": "Mã lỗi 50: T_BNTT trong XML2 không hợp lệ",
        "description": "",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "51",
        "rule_name": "Mã lỗi 51: T_NGUONKHAC trong XML2 không hợp lệ",
        "description": "So sánh T_NGUONKHAC phải thỏa mãn 0 <= T_NGUONKHAC<= THANH_TIEN\nKhông thỏa mãn thì vi phạm (TH thanh_tien <0 thì bỏ qua không chặn).",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "52",
        "rule_name": "Mã lỗi 52: Thành tiền trong XML3 không hợp lệ",
        "description": "Với XML3 thuộc 1 trong các trường hợp sau:\nMã nhóm =13\nMã nhóm = 15\nMã nhóm =8 và tỷ lệ thanh toán = 50 hoặc 80\nHồ sơ TYT có ngày vào kể từ ngày 15/07/2018, xml3 có mã nhóm =8 và tỷ lệ thanh toán =35\nHồ sơ TYT có ngày vào kể từ ngày 15/07/2018, xml3 có mã nhóm thuộc (1,2,3,8) và tỷ lệ thanh toán =70\nCác XML3 này vi phạm khi THANH_TIEN khác (so_luong * don_gia * tỷ lệ TT/100)\nCác XML3 còn lại không nằm trong các TH trên:\nVi phạm khi THANH_TIEN khác (so_luong * don_gia)",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "53",
        "rule_name": "Mã lỗi 53: T_BHTT trong XML3 không hợp lệ",
        "description": "Với XML3 thuộc 1 trong các trường hợp sau:\nMã nhóm =13\nMã nhóm = 15\nMã nhóm =8 và tỷ lệ thanh toán = 50 hoặc 80\nHồ sơ TYT có ngày vào kể từ ngày 15/07/2018, xml3 có mã nhóm =8 và tỷ lệ thanh toán =35\nHồ sơ TYT có ngày vào kể từ ngày 15/07/2018, xml3 có mã nhóm thuộc (1,2,3,8) và tỷ lệ thanh toán =70\nCác XML3 còn lại không nằm trong các TH trên (trừ các XML3 là VTYT nằm trong gói):",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "54",
        "rule_name": "Mã lỗi 54: T_BNCCT trong XML3 không hợp lệ",
        "description": "Với XML3 thuộc 1 trong các trường hợp sau:\nMã nhóm =13\nMã nhóm = 15\nMã nhóm =8 và tỷ lệ thanh toán = 50 hoặc 80\nHồ sơ TYT có ngày vào kể từ ngày 15/07/2018, xml3 có mã nhóm =8 và tỷ lệ thanh toán =35\nHồ sơ TYT có ngày vào kể từ ngày 15/07/2018, xml3 có mã nhóm thuộc (1,2,3,8) và tỷ lệ thanh toán =70\nCác XML3 còn lại không nằm trong các TH trên (trừ các XML3 là VTYT nằm trong gói):",
        "category": "FORMAT_LOGIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "55",
        "rule_name": "Mã lỗi 55: T_BNTT trong XML3 không hợp lệ",
        "description": "Chỉ xét với các XML3 không phải VTYT nằm trong gói:",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "56",
        "rule_name": "Mã lỗi 56: T_NGUONKHAC trong XML3 không hợp lệ",
        "description": "So sánh T_NGUONKHAC phải thỏa mãn 0 <= T_NGUONKHAC<= THANH_TIEN\nKhông thỏa mãn thì vi phạm (TH thanh_tien <0 thì bỏ qua không chặn).",
        "category": "ARITHMETIC",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "58",
        "rule_name": "Mã lỗi 58: Hồ sơ có ngày vào lớn hơn ngày hết hợp đồng của Cơ sở KCB",
        "description": "Kiểm tra ngày hết hợp đồng của Cơ sở KCB trong danh mục Cơ sở KCB, nếu ngày vào của hồ sơ lớn hơn ngày hết hợp đồng thì vi phạm.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "60",
        "rule_name": "Mã lỗi 60 (Cơ sở đăng ký khám ngoại trú nhận hồ sơ nội trú không hợp lệ)",
        "description": "Hồ sơ vi phạm nếu thỏa mãn tất cả các điều kiện sau:\nMã loại KCB = 3 (nội trú)\nCơ sở KCB đăng ký khám Ngoại trú\n(Trong bảng LOG_LOAIHOPDONG của cơ sở đó thỏa mãn: LOAI_HOPDONG = 0 và NGAY_VAO của hồ sơ nằm trong khoảng TU_NGAY, DEN_NGAY.\nTrường hợp trong bảng LOG_LOAIHOPDONG ko có bản ghi thỏa mãn thì tìm cơ sở kcb đó trong Danh mục cơ sở KCB, cơ sở có LOAI_HOPDONG = 0).\nTrên đây là danh sách toàn bộ các mã lỗi chặn hồ sơ, nếu các hồ sơ vi phạm các lỗi này, sẽ tự động bị xóa khỏi hệ thống giám định, đồng thời hệ thống giám định sẽ trả về mã lỗi và miêu tả cho tất cả các lỗi mà hồ sơ vi phạm về bên cổng tiếp nhận.\nCác hồ sơ không bị lỗi, không bị chặn lại qua quá trình kiểm tra lỗi hồ sơ sẽ tiếp tục chạy qua quá trình giám định tự động hiện tại.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "61",
        "rule_name": "Mã lỗi 61: Trùng hồ sơ",
        "description": "Phần này thực hiện đầu tiên trước khi làm các tác vụ khác, bộ key trùng: mã thẻ, họ tên, ngày vào, ngày ra, mã bệnh, mã cơ sở kcb, kỳ quyết toán, T_TONGCHI, T_BHTT.\nNếu tồn tại 1 bản ghi đã có tại giám định với cả 2 tiền T_TONGCHI và T_BHTT lệch nhau không quá 2 đồng thì trả về hồ sơ.",
        "category": "CROSS_RECORD_DUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "101",
        "rule_name": "Mã lỗi 101: (Bệnh nhân KCB ngoại trú trái tuyến, quỹ BHYT không thanh toán lý do vào viện Thông tuyến)",
        "description": "1.Không thanh toán các hồ sơ ngoại trú có lý do vào viện là thông tuyến tại bệnh viện tuyến huyện, tuyến tỉnh, tuyến TW.\n2.Đối Với mã loại KCB (MA_LOAI_KCB) = 1,2 AND Lý do vào viện (MA_LYDO_VVIEN) = 4 mới check.\nCheck điều kiện lấy ra tuyến CMKT của CSKCB:\nSelect TUYENCMKT from DM_COSOKCB_BC_THANG a where X1.MA_CSKCB = a.MA and subtr(X1.NGAY_VAO,0,6)= a.THANG_QT\n- If TUYENCMKT in (1,2)\n=> vi phạm quy tắc\n- If TUYENCMKT = 3\nSelect TUYENCMKT,MATINHTHANH from DM_COSOKCB a where X1.MA_DKBD = a.MA (1)\nSelect TUYENCMKT,MATINHTHANH from DM_COSOKCB a where X1.MA_CSKCB = a.MA (2)\n=> So sánh:\nTH1: MATINHTHANH (1) <> MATINHTHANH (2) => vi phạm quy tắc\nTH2: MATINHTHANH (1) = MATINHTHANH (2)\nNếu TUYENCMKT (1) in (1,2) = > vi phạm quy tắc\nMã lỗi: 102: VTYT đi kèm DVKT không có trong hồ sơ\nCheck HS có ngày vào từ 1/8/2021\nCheck XML3_4210 các chi phí có mã nhóm = 10,11\nCheck MA_DICH_VU nếu trống bỏ qua nếu có lấy ra thông tin MA_DICH_VU rồi check tiếp xem MA_DICH_VU có xuất hiện ở XML3_4210 có mã nhóm khác 10,11 của hồ sơ đấy ko\nselect * from XML3_4210 where xml1_4210_ID = 'ID của hồ sơ đang check' and ma_nhom not in (10,11) and ma_dich_vu = 'ma_dich_vu của VTYT đang check'\nNếu có bỏ qua ko thì vi phạm.\nMã lỗi mới 103: Đề nghị TT hồ sơ khác năm tài chính.\nCheck ngày ra của hồ sơ ( chỉ check năm ) nếu khác năm hiện tại thì trả về cổng mã lỗi 103, tinhtranggui = 6.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "104",
        "rule_name": "Mã lỗi 104: Sai mã loại KCB với tuyến BV (Mã loại KCB = 5 không phải tuyến xã, PKĐKKV)",
        "description": "Từ X1.MA_CSKCB tìm trong bảng DM_COSOKCB lấy ra TUYENCMKT và KIEUBV\nNếu X1.MA_LOAI_KCB = 5 AND (TUYENCMKT = 4 AND KIEUBV = 7 OR TUYENCMKT = 3 AND KIEUBV = 2) thì pass ko thì vi phạm.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "105",
        "rule_name": "Mã lỗi 105: Sai mã loại KCB, Mã loại KCB đúng = 5.",
        "description": "Từ X1.MA_CSKCB tìm trong bảng DM_COSOKCB lấy ra TUYENCMKT và KIEUBV\nNếu (TUYENCMKT = 4 AND KIEUBV = 7 OR TUYENCMKT = 3 AND KIEUBV = 2) AND Có xuất hiện từ 1 bản ghi X3.MA_DICH_VU = 'TYT.1925' or 'PKKV.1925' AND X1.MA_LOAI_KCB <> 5 thì vi phạm.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4210",
        "rule_code": "106",
        "rule_name": "Mã lỗi 106: Sai mã loại KCB, Mã loại KCB đúng phải khác 5.",
        "description": "Từ X1.MA_CSKCB tìm trong bảng DM_COSOKCB lấy ra TUYENCMKT và KIEUBV\nNếu (TUYENCMKT = 4 AND KIEUBV = 7 OR TUYENCMKT = 3 AND KIEUBV = 2) AND X1.MA_LOAI_KCB = 5 AND Ko có bản ghi nào thỏa mãn X3.MA_DICH_VU = 'TYT.1925' or 'PKKV.1925' thì vi phạm.",
        "category": "CATALOG_LOOKUP",
        "source": "GDH_Danh sách các mã lỗi Chặn hồ sơ sai logic.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "1",
        "rule_name": "Mã lỗi 1: Sai lý do vào viện (Sai đối tượng KCB)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nMã lý do vào viện đề nghị ko nằm trong list: Select MA_CHA from DM_DOITUONG_KCB where HIEULUC = 1;\nMã lý do vào viện đề nghị =3 nhưng Mã ĐKBĐ = Mã CSKCB (Đúng tuyến mà gửi lên là trái tuyến).",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "8",
        "rule_name": "Mã lỗi 8: Sai thông tin thẻ (CTN)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nTrong danh mục mức hưởng BHYT, không tìm thấy bản ghi có hiệu lực và có mã = 3 ký tự đầu thẻ BHYT.\nTrong danh mục đơn vị BHXH, không tim thấy bản ghi có mã đơn vị = 2 ký tự thứ 4, 5 của mã thẻ BHYT.\n10 ký tự cuối không phải ký tự số hoặc = 0000000000",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "9",
        "rule_name": "Mã lỗi 9 (Sai thông tin CSKCB ban đầu) (CTN)",
        "description": "Với các hồ sơ thỏa mãn tất cả các điều kiện sau sẽ bỏ qua không xét mã lỗi này:\n2 ký tự thứ 4, 5 của mã thẻ == DM_TINHTHANH.MA.\n3 ký tự đầu mã thẻ là TE1, HG4 và QTTHE = 700000 và mã đk ban đầu có định dạng XX000 trong đó XX = =DM_TINHTHANH.MA == 2 ký tự thứ 4, 5 của mã thẻ.\nCác hồ sơ không thuộc trường hợp trên thì xét tiếp, nếu vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nKhông tìm thấy mã ĐKBĐ của hồ sơ trong danh mục Cơ sở kcb.\nHồ sơ có Mã ĐKBĐ khác, nhưng dữ liệu ở trường này: các mã CSKCB không cách nhau bởi dấu “;”\nHồ sơ có Mã ĐKBĐ khác, dữ liệu ở trường này: các mã CSKCB cách nhau bởi dấu “;”.\nNhưng trong số các mã CSKCB đó, tồn tại ít nhất 1 mã CSKCB không có trong danh mục CSKCB.",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "10",
        "rule_name": "Mã lỗi 10 (Sai thông tin CSKCB)",
        "description": "Hồ sơ vi phạm mã lỗi trên khi: mã CSKCB của hồ sơ không tìm thấy trong danh mục CSKCB.",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "11",
        "rule_name": "Mã lỗi 11 (Hồ sơ không phát sinh chi phí Đề nghị thanh toán)",
        "description": "Hồ sơ vi phạm trường hợp sau sẽ bị trả về mã lỗi trên: tiền đề nghị BHTT trống hoặc =0",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "14",
        "rule_name": "Mã lỗi 14 (Stent động mạch vành phủ thuốc các cỡ các loại thanh toán theo TT 04/2017/TT-BYT)",
        "description": "Hồ sơ vi phạm mã lỗi trên khi: đề nghị chi phí VTYT STENT mã “N06.02.020’ với số lượng > 1\n(bỏ qua xét mã lỗi này với các hồ sơ có mã thẻ là CC1, TE1, QN5, CA5, CY5)",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "15",
        "rule_name": "Mã lỗi 15 (Ngày sinh không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường ngày sinh không đúng 8  ký tự số\nGiá trị trường ngày sinh không hợp lệ (ví dụ 20170135: ngày 35/1/2017)\nNgày sinh lớn hơn ngày hiện tại",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "16",
        "rule_name": "Mã lỗi 16 (giới tính không hợp lệ) (CTN)",
        "description": "Hồ sơ vi phạm khi: giá trị giới tính đề nghị khác (1,2,3)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "17",
        "rule_name": "Mã lỗi 17 (Mã thẻ không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Mã thẻ không đúng 15 ký tự\nGiá trị trường Mã thẻ khác không null, nhưng các mã thẻ trong trường mã thẻ khác không cách nhau bởi dấu “;”\nGiá trị trường Mã thẻ khác không null, các mã thẻ trong trường mã thẻ khác cách nhau bởi dấu “;”. Nhưng trong đó tồn tại 1 giá trị mã thẻ không đúng 15 ký tự.\nGiá trị thứ 4,5 trường Mã thẻ ko nằm trong list\nSelect MA from DM_TINHTHANH where HIEULUC = 1.\n10 ký tự cuối ko phải là số hoặc toàn là số 0.",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "18",
        "rule_name": "Mã lỗi 18 (giá trị thẻ từ không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường giá trị thẻ từ khác không null, nhưng các giá trị trong trường này không cách nhau bởi dấu “;”\nGiá trị trường giá trị thẻ từ khác không null, các giá trị trong trường này cách nhau bởi dấu “;”, nhưng trong đó tồn tại 1 giá trị không đúng 8 ký tự số.\nGiá trị trường giá trị thẻ từ khác không null, các giá trị trong trường này cách nhau bởi dấu “;”,nhưng trong đó tồn tại 1 giá trị không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "19",
        "rule_name": "Mã lỗi 19 (giá trị thẻ đến không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường giá trị thẻ đến khác không null, nhưng các giá trị trong trường này không cách nhau bởi dấu “;”\nGiá trị trường giá trị thẻ đến khác không null, các giá trị trong trường này cách nhau bởi dấu “;”, nhưng trong đó tồn tại 1 giá trị không đúng 8 ký tự số.\nGiá trị trường giá trị thẻ đến khác không null, các giá trị trong trường này cách nhau bởi dấu “;”,nhưng trong đó tồn tại 1 giá trị không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "20",
        "rule_name": "Mã lỗi 20 (Số lượng mã thẻ và các thông tin thẻ không tương ứng)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nNếu trong 4 trường XML1.MA_THE_KHAC, XML1.MA_DKBD_KHAC, XML1.GT_THE_TU_KHAC, XML1.GT_THE_DEN_KHAC có trường rỗng, nhưng các trường còn lại vẫn có giá trị\nTách các giá trị trong 4 trường trên theo dấu “;”,thành danh sách các giá trị cụ thể. Nếu số lượng bốn danh sách tách được không bằng nhau (ví dụ 4 mã thẻ, 3 cơ sở ĐKBĐ, 5 giá trị từ, 5 giá trị đến)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "21",
        "rule_name": "Mã lỗi 21 (Miễn cùng chi trả không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Miễn cùng chi trả không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "22",
        "rule_name": "Mã lỗi 22 (Mã tai nạn không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường mã tại nạn không thuộc List\nselect MA from DM_MA_TAINAN where HIEULUC =1;",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "23",
        "rule_name": "Mã lỗi 23 (Ngày vào không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Ngày vào không hợp lệ (ví dụ 201701351212: ngày 35/1/2017 12h12p\nHoặc 201701302555: ngày 30/01/2017 25h55p)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "24",
        "rule_name": "Mã lỗi 24 (Ngày ra không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Ngày ra không hợp lệ (ví dụ 201701351212: ngày 35/1/2017 12h12p\nHoặc 201701302555: ngày 30/01/2017 25h55p)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "25",
        "rule_name": "Mã lỗi 25 (Kết quả điều trị không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường ko nằm trong list:\nselect MA from DM_KETQUA_DIEUTRI where HIEULUC = 1;",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "26",
        "rule_name": "Mã lỗi 26 (Tình trạng ra viện không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường Tình trạng ra viện không thuộc list:\nselect MA from DM_MA_LOAI_RV where HIEULUC = 1;",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "27",
        "rule_name": "Mã lỗi 27 (Ngày thanh toán không hợp lệ)",
        "description": "Hồ sơ vi phạm 1 trong các trường hợp sau sẽ bị trả về mã lỗi trên:\nGiá trị trường Ngày thanh toán không hợp lệ (ví dụ 201701351212: ngày 35/1/2017 12h12p\nHoặc 201701302555: ngày 30/01/2017 25h55p)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "31",
        "rule_name": "Mã lỗi 31 (T_BHTT trong XML1 khác tổng cộng các T_BHTT trong XML23)",
        "description": "Hồ sơ vi phạm khi:\nT_BHTT trong xml1 != Tổng (T_BHTT) trong xml2 + Tổng (T_BHTT) trong xml3",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "34",
        "rule_name": "Mã lỗi 34 (T_TONGCHI_BV trong XML1 khác tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC)",
        "description": "Hồ sơ vi phạm khi:\nT_TONGCHI_BV != T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "35",
        "rule_name": "Mã lỗi 35 (Năm quyết toán không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Năm quyết toán > Năm hiện tại.",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "36",
        "rule_name": "Mã lỗi 36 (Tháng quyết toán không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Tháng quyết toán không thuộc các giá trị từ 1đến 12.",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "37",
        "rule_name": "Mã lỗi 37 (Mã loại KCB không hợp lệ)",
        "description": "Hồ sơ vi phạm khi giá trị trường Mã loại KCB không thuộc Danh mục theo Quyết định 824/BYT",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "38",
        "rule_name": "Mã lỗi 38 (Mã KHU VỰC không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: giá trị trường Mã khu vực không thuộc các giá trị (K1, K2, K3)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "39",
        "rule_name": "Mã lỗi 39 (Mã nhóm trong XML2 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML2 có giá trị Mã nhóm khác (4,7,17)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "40",
        "rule_name": "Mã lỗi 40 (Phạm vi trong XML2 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML2 có giá trị trường Phạm vi ko thuộc các giá trị (1,2,3)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "43",
        "rule_name": "Mã lỗi 43 (Mã nhóm trong XML3 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML3 có giá trị Mã nhóm khác (1, 2, 3, 8,10, 12, 13, 14, 15,16,18,19)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "44",
        "rule_name": "Mã lỗi 44 (Phạm vi trong XML3 không hợp lệ)",
        "description": "Hồ sơ vi phạm khi: tồn tại ít nhất 1 bản ghi trong XML3 có giá trị trường Phạm vi ko thuộc các giá trị (1,2,3)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "47",
        "rule_name": "Mã lỗi 47: Thành tiền trong XML2 không hợp lệ",
        "description": "XML2 vi phạm khi THANH_TIEN_BV !=  (so_luong * don_gia)\nHoặc THANH_TIEN_BV trong XML2 != Tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC\nHoặc THANH_TIEN_BH != so_luong * don_gia * TY_LE/100",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "48",
        "rule_name": "Mã lỗi 48: T_BHTT trong XML2 không hợp lệ",
        "description": "Bước 1: Tạm tính:\nT_BNTT =  THANH_TIEN_BV – THANH_TIEN_BH\nT_BHTT = Round((THANH_TIEN_BH * MUC_HUONG/100),2)\nT_BNCCT = THANH_TIEN_BH - T_BHTT\nBước 2: So sánh đối chiếu tiếp",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "49",
        "rule_name": "Mã lỗi 49: T_BNCCT trong XML2 không hợp lệ",
        "description": "Bước 1: Tạm tính:\nT_BNTT =  THANH_TIEN_BV – THANH_TIEN_BH\nT_BHTT = Round((THANH_TIEN_BH * MUC_HUONG/100),2)\nT_BNCCT = THANH_TIEN_BH - T_BHTT\nBước 2: So sánh đối chiếu tiếp",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "50",
        "rule_name": "Mã lỗi 50: T_BNTT trong XML2 không hợp lệ",
        "description": "TH1: 0 <= T_NGUONKHAC < T_BNTT\nVi phạm khi XML3 tồn tại 1 bản ghi T_BNTT !=  THANH_TIEN_BV – THANH_TIEN_BH - T_NGUONKHAC\nTH2: T_NGUONKHAC >= T_BNTT\nVi phạm khi XML3 tồn tại 1 bản ghi T_BNTT !=  0",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "51",
        "rule_name": "Mã lỗi 51: T_NGUONKHAC trong XML2 không hợp lệ",
        "description": "So sánh T_NGUONKHAC phải thỏa mãn 0 <= T_NGUONKHAC<= THANH_TIEN_BV hoặc\nT_NGUONKHAC != T_NGUONKHAC_CL+ T_NGUONKHAC_NSNN + T_NGUONKHAC_VTNN+ T_NGUONKHAC_VTTN",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "52",
        "rule_name": "Mã lỗi 52: Thành tiền trong XML3 không hợp lệ",
        "description": "Các XML3 này vi phạm khi THANH_TIEN_BV != (so_luong * DON_GIA_DV * TYLE_TT_DV /100) hoặc (SO_LUONG * DON_GIA_BV - SO_LUONG * DON_GIA_BH * (100 - TYLE_TT_DV)/100) hoặc (so_luong * DON_GIA_BV)\nhoặc THANH_TIEN_BV trong XML3 != Tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "53",
        "rule_name": "Mã lỗi 53: T_BHTT trong XML3 không hợp lệ",
        "description": "Với XML3 trừ các XML3 là VTYT nằm trong gói:\nBước 1: Tạm tính:\nT_BNTT =  THANH_TIEN_BV – THANH_TIEN_BH\nT_BHTT = Round((THANH_TIEN_BH * MUC_HUONG/100),2)\nT_BNCCT = THANH_TIEN_BH - T_BHTT\nBước 2: So sánh đối chiếu tiếp",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "55",
        "rule_name": "Mã lỗi 55: T_BNCCT trong XML3 không hợp lệ",
        "description": "Bước 1: Tạm tính:\nVới XML3 trừ các XML3 là VTYT nằm trong gói:\nT_BNTT =  THANH_TIEN_BV – THANH_TIEN_BH\nT_BHTT = Round((THANH_TIEN_BH * MUC_HUONG/100),2)\nT_BNCCT = THANH_TIEN_BH - T_BHTT\nBước 2: So sánh đối chiếu tiếp",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "54",
        "rule_name": "Mã lỗi 54: T_BNTT trong XML3 không hợp lệ",
        "description": "TH1: 0 <= T_NGUONKHAC < T_BNTT\nVi phạm khi XML3 tồn tại 1 bản ghi T_BNTT !=  THANH_TIEN_BV – THANH_TIEN_BH - T_NGUONKHAC\nTH2: T_NGUONKHAC >= T_BNTT\nVi phạm khi XML3 tồn tại 1 bản ghi T_BNTT !=  0",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "56",
        "rule_name": "Mã lỗi 56: T_NGUONKHAC trong XML3 không hợp lệ",
        "description": "So sánh T_NGUONKHAC phải thỏa mãn 0 <= T_NGUONKHAC<= THANH_TIEN_BV hoặc\nT_NGUONKHAC != T_NGUONKHAC_CL+ T_NGUONKHAC_NSNN + T_NGUONKHAC_VTNN+ T_NGUONKHAC_VTTN",
        "category": "ARITHMETIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "58",
        "rule_name": "Mã lỗi 58: Hồ sơ có ngày vào lớn hơn ngày hết hợp đồng của Cơ sở KCB (GĐ)",
        "description": "Kiểm tra ngày hết hợp đồng của Cơ sở KCB trong danh mục Cơ sở KCB, nếu ngày vào của hồ sơ lớn hơn ngày hết hợp đồng thì vi phạm.",
        "category": "CATALOG_LOOKUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "60",
        "rule_name": "Mã lỗi 60 (Cơ sở đăng ký khám ngoại trú nhận hồ sơ nội trú không hợp lệ)  (GĐ)",
        "description": "Hồ sơ vi phạm nếu thỏa mãn tất cả các điều kiện sau:\nMã loại KCB = 3,4,9 (nội trú)\nCơ sở KCB đăng ký khám Ngoại trú",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "61",
        "rule_name": "Mã lỗi 61: Trùng hồ sơ (GĐ)",
        "description": "Phần này thực hiện đầu tiên trước khi làm các tác vụ khác, bộ key trùng: mã thẻ, họ tên, ngày vào,kỳ QT, Mã CSKCB\nNếu tồn tại 1 bản ghi đã có tại giám định trả về hồ sơ.\nMã lỗi: 102: VTYT đi kèm DVKT không có trong hồ sơ (CTN)\nCheck XML3_4210 các chi phí có mã nhóm = 10,11\nCheck MA_DICH_VU nếu trống bỏ qua nếu có lấy ra thông tin MA_DICH_VU rồi check tiếp xem MA_DICH_VU có xuất hiện ở XML3 có mã nhóm khác 10,11 của hồ sơ đấy ko\nNếu ko có thì vi phạm.\nMã lỗi mới 103: Đề nghị TT hồ sơ khác năm tài chính. (GĐ)\nCheck ngày ra của hồ sơ ( chỉ check năm ) nếu khác NAM_QT (năm quyết toán) của hồ sơ thì vi phạm.\nLưu ý: ngày ra 25/12-31/12 của năm liền kề trước năm quyết toán trong hồ sơ thì bỏ qua quy tắc.",
        "category": "CROSS_RECORD_DUP",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "108",
        "rule_name": "Mã lỗi 108: Năm sinh < 1900 (CTN)",
        "description": "If TO_NUMBER(SUBSTR(ngay_sinh,1,4)) < 1900\n=> Vi phạm mã lỗi 108",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "109",
        "rule_name": "Mã lỗi 109: ngay_sinh > ngay_vao",
        "description": "Nếu ngày sinh > ngày vào\n=> Vi phạm mã lỗi 109",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "110",
        "rule_name": "Mã lỗi 110: Thẻ Bộ CA cấp không phải thẻ CA",
        "description": "Check XML1_4210 có ngày vào từ 1/12/2021\nIf substr(ma_the,4,2) ='98' AND substr(ma_the,1,3) !='CA5'\nIf substr(ma_the, 1,3) ='CA5' AND substr(ma_the,4,2) !='98'\n=> Vi phạm",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "111",
        "rule_name": "Mã lỗi 111: Thẻ TQ/QN sai mã tỉnh trên thẻ",
        "description": "If (substr(ma_the,4,2) !='97' AND substr(ma_the,1,2) in ('QN', 'TQ')) Or\n(substr(ma_the,4,2) ='97' AND substr(ma_the,1,2) not in\n('BT','DN','HC','HS','LS','QN','SV','TE','TQ','TV','TY','XK'))\n=> Vi phạm",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "112",
        "rule_name": "Mã lỗi 112: Hưu trí nhỏ hơn 33 tuổi",
        "description": "If substr(ma_the,1,2) ='HT'\nand SUBSTR(NGAY_VAO,1,4) - TO_NUMBER(SUBSTR(ngay_sinh,1,4)) < 33\n=> Vi phạm",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "113",
        "rule_name": "Mã lỗi 113: Thẻ CT phải đủ 80 tuổi",
        "description": "If substr(ma_the,1,2) ='CT'\nand SUBSTR(NGAY_VAO,1,4) - TO_NUMBER(SUBSTR(ngay_sinh,1,4)) < 80\n=> Vi phạm",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "114",
        "rule_name": "Mã lỗi 114: Trẻ em sử dụng thẻ tạm:",
        "description": "Mã tỉnh trên thẻ <> Mã tỉnh tại mã ĐKBD thì vi phạm quy tắc",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "115",
        "rule_name": "Mã lỗi 115: Hồ sơ khám bệnh có tiền giường",
        "description": "If t_giuong>0 and ma_loai_kcb in (1,7) => Vi phạm",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "116",
        "rule_name": "Mã lỗi 116: Có tiền vận chuyển nhưng tien_ngoaids <= 0",
        "description": "If t_van_chuyen>0 and tien_ngoai_ds =0 => Vi phạm",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "117",
        "rule_name": "Mã lỗi 117: năm năm liên lục không hợp lệ:",
        "description": "Giá trị trường NAM_NAM_LIEN_TUC không hợp lệ (ví dụ 20170135: ngày 35/1/2017)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "118",
        "rule_name": "Mã lỗi 118 (Ngày y lệnh hoặc ngày thực hiện y lệnh ở XML2 không hợp lệ)",
        "description": "Hồ sơ vi phạm nếu có 1 bản ghi ở XML2 vi phạm:\nGiá trị trường NGAY_YL_NUMBER hoặc NGAY_TH_YL không hợp lệ (ví dụ 201701351212: ngày 35/1/2017 12h12p\nHoặc 201701302555: ngày 30/01/2017 25h55p)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "119",
        "rule_name": "Mã lỗi 119 (Ngày y lệnh hoặc ngày thực hiện y lệnh ở XML3 không hợp lệ)",
        "description": "Hồ sơ vi phạm nếu có 1 bản ghi ở XML3 vi phạm:\nGiá trị trường NGAY_YL_NUMBER hoặc NGAY_TH_YL không hợp lệ (ví dụ 201701351212: ngày 35/1/2017 12h12p\nHoặc 201701302555: ngày 30/01/2017 25h55p)",
        "category": "FORMAT_LOGIC",
        "source": "TLGDH_Danh sách mã lỗi chặn hồ sơ sai Logic theo 4750.docx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_REQ_XML1",
        "rule_name": "Kiểm tra các trường bắt buộc Bảng 1 (XML1)",
        "description": "Bắt buộc có dữ liệu: MA_LK, MA_CSKCB, MA_BN, HO_TEN, NGAY_SINH, GIOI_TINH, DIA_CHI, NGAY_VAO, NGAY_RA, MA_LOAI_KCB, MA_BENH_CHINH, KET_QUA_DTRI, TINH_TRANG_RV theo QĐ 4750.",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_REQ_XML2",
        "rule_name": "Kiểm tra các trường bắt buộc Bảng 2 (Thuốc)",
        "description": "Bắt buộc có dữ liệu: MA_THUOC, TEN_THUOC, HAM_LUONG, DON_VI_TINH, SO_LUONG, DON_GIA, TYLE_TT, THANH_TIEN, MA_KHOA.",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_REQ_XML3",
        "rule_name": "Kiểm tra các trường bắt buộc Bảng 3 (DVKT, VTYT)",
        "description": "Bắt buộc có dữ liệu: MA_DICH_VU, TEN_DICH_VU, SO_LUONG, DON_GIA, TYLE_TT, THANH_TIEN, MA_KHOA.",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_CCCD_FORMAT",
        "rule_name": "Kiểm tra định dạng số CCCD / CMND / Hộ chiếu",
        "description": "Định dạng 9 hoặc 12 ký tự số, hoặc 8 ký tự bắt đầu bằng chữ hoa + 7 ký tự số.",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_CROSS_CONSISTENCY",
        "rule_name": "Tính nhất quán nhân thân giữa XML1 và các bảng phụ",
        "description": "HO_TEN, NGAY_SINH, GIOI_TINH ở các bảng XML 6, 7, 8, 9, 13, 14, 15 nếu có dữ liệu thì bắt buộc phải trùng khớp với Bảng 1 (XML1).",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_XML8_APPLICABILITY",
        "rule_name": "Điều kiện áp dụng Bảng 8 (Tóm tắt HSBA)",
        "description": "Bảng 8 chỉ được phép xuất hiện khi MA_LOAI_KCB ở XML1 thuộc ('03', '04', '06') (Nội trú / Ban ngày).",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    },
    {
        "standard": "4750",
        "rule_code": "CTN_XML14_APPOINTMENT_DATE",
        "rule_name": "Ràng buộc thời điểm hẹn khám lại (Bảng 14)",
        "description": "Thời điểm hẹn khám lại (NGAY_HEN_KL) ở Bảng 14 bắt buộc phải lớn hơn ngày ra viện (NGAY_RA) của đợt KCB.",
        "category": "FORMAT_LOGIC",
        "source": "QD4750_Check_Validate CTN QĐ_4750.xlsx",
        "is_active": True
    }
]

def get_rules_for_standard(standard: str) -> list:
    return [r for r in RULE_CATALOG if r["standard"] == standard and r.get("is_active", True)]

def get_rule_catalog() -> list:
    return RULE_CATALOG

# =============================================================================
# MA TRẬN BẢNG XML PHỤ THUỘC (RULE -> REQUIRED TABLES)
# Định nghĩa danh sách các bảng XML bắt buộc phải truy vấn thành công.
# Nếu bất kỳ bảng nào trong danh sách bị lỗi truy vấn từ SQL Server,
# quy tắc đó KHÔNG ĐƯỢC PHÉP trả về PASSED (buộc hạ xuống INCOMPLETE_DATA).
# =============================================================================
RULE_REQUIRED_TABLES_MAP = {
    # Nhóm quy tắc tính tiền và đối chiếu chi tiết thuốc / DVKT
    "3": ["XML2", "XML3"],
    "4": ["XML1", "XML2", "XML3"],
    "10": ["XML1", "XML3"],
    "12": ["XML1", "XML2", "XML3"],
    "14": ["XML3"],
    "31": ["XML1", "XML2", "XML3"],
    "39": ["XML2"],
    "40": ["XML2"],
    "41": ["XML2"],
    "42": ["XML2"],
    "43": ["XML3"],
    "44": ["XML3"],
    "45": ["XML3"],
    "46": ["XML3"],
    "47": ["XML2"],
    "48": ["XML2"],
    "49": ["XML2"],
    "50": ["XML2"],
    "51": ["XML2"],
    "52": ["XML3"],
    "53": ["XML3"],
    "54": ["XML3"],
    "55": ["XML3"],
    "56": ["XML3"],
    "105": ["XML1", "XML3"],
    "106": ["XML1", "XML3"],
    "115": ["XML1", "XML3"],
    "118": ["XML2"],
    "119": ["XML3"],

    # Nhóm quy tắc đối chiếu chéo và kiểm tra theo CTN 4750
    "CTN_REQ_XML1": ["XML1"],
    "CTN_REQ_XML2": ["XML2"],
    "CTN_REQ_XML3": ["XML3"],
    "CTN_CCCD_FORMAT": ["XML1"],
    "CTN_CROSS_CONSISTENCY": ["XML1", "XML6", "XML7", "XML8", "XML9", "XML13", "XML14", "XML15"],
    "CTN_XML8_APPLICABILITY": ["XML1", "XML8"],
    "CTN_XML14_APPOINTMENT_DATE": ["XML1", "XML14"],
}

def get_rule_required_tables(standard: str, rule_code: str) -> list:
    """Trả về danh sách bảng XML phụ thuộc của một quy tắc"""
    # 1. Tìm chính xác theo cặp (standard, rule_code)
    key_std = f"{standard}_{rule_code}"
    if key_std in RULE_REQUIRED_TABLES_MAP:
        return RULE_REQUIRED_TABLES_MAP[key_std]
    
    # 2. Tìm theo rule_code độc lập
    if rule_code in RULE_REQUIRED_TABLES_MAP:
        return RULE_REQUIRED_TABLES_MAP[rule_code]

    # 3. Mặc định hầu hết các quy tắc hành chính / tổng hợp đều dựa vào XML1
    return ["XML1"]

