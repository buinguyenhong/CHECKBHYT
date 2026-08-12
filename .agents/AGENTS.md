# Agent Rules & Guidelines - CheckBHYT

## 1. Đồng bộ Kiến thức & Tài liệu khi thay đổi (MANDATORY)

- **Nguyên tắc cốt lõi:** Khi có bất kỳ thay đổi nào về mã nguồn, cấu hình, CSDL, Stored Procedures, API, hoặc quy trình nghiệp vụ:
  1. **Ghi log changelog:** Thêm mốc thay đổi vào [AGENT_CHANGELOG.md](file:///d:/Project/newcheckBHYT/CHECKBHYT/CHECKBHYT/AGENT_CHANGELOG.md).
  2. **Cập nhật tài liệu kiến thức gốc (BẮT BUỘC):** Phải cập nhật trực tiếp và ngay lập tức các tệp tài liệu chính bao gồm [Project.md](file:///d:/Project/newcheckBHYT/CHECKBHYT/CHECKBHYT/Project.md), [INSTALL_WEB.md](file:///d:/Project/newcheckBHYT/CHECKBHYT/CHECKBHYT/INSTALL_WEB.md), và [xml_validation_tool_spec.md](file:///d:/Project/newcheckBHYT/CHECKBHYT/CHECKBHYT/xml_validation_tool_spec.md).
  3. **Tuyệt đối không để xảy ra mâu thuẫn:** Thông tin trong tệp kiến thức dự án (`Project.md`) phải luôn đồng nhất 100% với mã nguồn thực tế và nhật ký `AGENT_CHANGELOG.md`.

## 2. Kiểm tra trước khi trả lời & thực thi

- Trước khi tư vấn hoặc trả lời câu hỏi về dự án, Agent phải đối chiếu giữa `AGENT_CHANGELOG.md` và `Project.md` cũng như mã nguồn thực tế (`models.py`, `his_service.py`, `main.py`,...) để đảm bảo thông tin đưa ra hoàn toàn chính xác.
