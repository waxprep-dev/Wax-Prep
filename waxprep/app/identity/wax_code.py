import random
import string
from datetime import datetime
from waxprep.app.core.constants import Platform, WAX_CODE_PREFIX, WAX_CODE_WHATSAPP_SUFFIX, WAX_CODE_TELEGRAM_SUFFIX, DEFAULT_REGION_CODE


def generate_wax_code(platform: Platform, phone_number: str = None) -> str:
    region_code = _extract_region_code(phone_number)
    year_part = "0000"
    random_part = _generate_random_string(6)
    platform_suffix = WAX_CODE_WHATSAPP_SUFFIX if platform == Platform.WHATSAPP else WAX_CODE_TELEGRAM_SUFFIX

    return f"{WAX_CODE_PREFIX}-{region_code}-{year_part}-{random_part}-{platform_suffix}"


def _extract_region_code(phone_number: str = None) -> str:
    if not phone_number:
        return DEFAULT_REGION_CODE

    if phone_number.startswith("234") or phone_number.startswith("+234"):
        return "NG"
    elif phone_number.startswith("233") or phone_number.startswith("+233"):
        return "GH"
    elif phone_number.startswith("232") or phone_number.startswith("+232"):
        return "SL"
    elif phone_number.startswith("220") or phone_number.startswith("+220"):
        return "GM"
    else:
        return DEFAULT_REGION_CODE


def _generate_random_string(length: int) -> str:
    characters = string.ascii_uppercase + string.digits
    characters = characters.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(random.choices(characters, k=length))


def update_wax_code_with_year(wax_code: str, birth_year: int) -> str:
    parts = wax_code.split("-")
    if len(parts) != 5:
        return wax_code
    parts[2] = str(birth_year)
    return "-".join(parts)


def validate_wax_code(wax_code: str) -> bool:
    parts = wax_code.split("-")
    if len(parts) != 5:
        return False
    if parts[0] != WAX_CODE_PREFIX:
        return False
    if len(parts[2]) != 4:
        return False
    if len(parts[3]) != 6:
        return False
    if parts[4] not in [WAX_CODE_WHATSAPP_SUFFIX, WAX_CODE_TELEGRAM_SUFFIX]:
        return False
    return True
