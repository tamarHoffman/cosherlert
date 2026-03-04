def build_pre_warning_message(zones: list[str]) -> str:
    zones_str = ", ".join(zones)
    return (
        f"התראה מפיקוד העורף: "
        f"בדקות הקרובות צפויות התרעות באזורי {zones_str}. "
        f"יש להתקרב למרחב המוגן הקרוב."
    )
