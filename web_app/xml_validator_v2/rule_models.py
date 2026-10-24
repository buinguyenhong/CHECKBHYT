from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

class RuleStatus(str, Enum):
    PASSED = "PASSED"
    VIOLATED = "VIOLATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPLETE_DATA = "INCOMPLETE_DATA"

@dataclass
class RuleViolation:
    standard: str
    rule_code: str
    rule_name: str
    xml_table: str
    field_name: str
    actual_value: str
    expected_condition: str
    message: str
    severity: str = "ERROR"

@dataclass
class RuleResult:
    rule_code: str
    standard: str
    rule_name: str
    status: RuleStatus
    violations: List[RuleViolation] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    reason: str = ""

@dataclass
class CaseXmlData:
    ma_lk: str
    ho_ten: str = ""
    loai_ca: str = ""  # 'Ngoại trú' | 'Nội trú'
    ma_the: str = ""
    ngay_ra_vien: Optional[str] = None
    xml1: Optional[Dict[str, Any]] = None
    xml2: List[Dict[str, Any]] = field(default_factory=list)
    xml3: List[Dict[str, Any]] = field(default_factory=list)
    xml4: List[Dict[str, Any]] = field(default_factory=list)
    xml5: List[Dict[str, Any]] = field(default_factory=list)
    xml6: List[Dict[str, Any]] = field(default_factory=list)
    xml7: List[Dict[str, Any]] = field(default_factory=list)
    xml8: List[Dict[str, Any]] = field(default_factory=list)
    xml9: List[Dict[str, Any]] = field(default_factory=list)
    xml10: List[Dict[str, Any]] = field(default_factory=list)
    xml11: List[Dict[str, Any]] = field(default_factory=list)
    xml12: List[Dict[str, Any]] = field(default_factory=list)
    xml13: List[Dict[str, Any]] = field(default_factory=list)
    xml14: List[Dict[str, Any]] = field(default_factory=list)
    xml15: List[Dict[str, Any]] = field(default_factory=list)
    raw_tables: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def get_table(self, name: str) -> List[Dict[str, Any]]:
        name_clean = name.upper().split("_")[0]
        if name_clean == "XML1":
            return [self.xml1] if self.xml1 else []
        if hasattr(self, name_clean.lower()):
            val = getattr(self, name_clean.lower())
            if isinstance(val, list) and len(val) > 0:
                return val
        return self.raw_tables.get(name_clean, [])

def to_decimal(val: Any, default: Decimal = Decimal("0.0")) -> Decimal:
    if val is None or val == "":
        return default
    try:
        s = str(val).strip().replace(",", ".")
        return Decimal(s)
    except Exception:
        return default

def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
