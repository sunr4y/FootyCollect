from django.utils.translation import gettext as _

COLOR_NAME_TO_MSGID = {
    "WHITE": "White",
    "RED": "Red",
    "BLUE": "Blue",
    "BLACK": "Black",
    "YELLOW": "Yellow",
    "GREEN": "Green",
    "SKY_BLUE": "Sky blue",
    "NAVY": "Navy",
    "ORANGE": "Orange",
    "GRAY": "Gray",
    "CLARET": "Claret",
    "PURPLE": "Purple",
    "PINK": "Pink",
    "BROWN": "Brown",
    "GOLD": "Gold",
    "SILVER": "Silver",
    "OFF_WHITE": "Off-white",
}


def get_color_display_name(name: str | None) -> str:
    if not name:
        return ""
    return _(COLOR_NAME_TO_MSGID.get(str(name).upper(), name))
