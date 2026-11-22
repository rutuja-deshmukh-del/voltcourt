from dataclasses import dataclass


@dataclass
class Bill:
    consumer_no: str
    prev_reading: float
    curr_reading: float
    units_billed: float
    billing_days: int
    energy_charge: float
    fixed_charge: float
    duty: float
    total_payable: float
    meter_status: str = "normal"   # normal / faulty / estimated