BUSINESS_INFO = {
    "name": "Maple Street Dog Grooming",

    "hours": {
        "monday": "9:00 AM - 6:00 PM",
        "tuesday": "9:00 AM - 6:00 PM",
        "wednesday": "9:00 AM - 6:00 PM",
        "thursday": "9:00 AM - 6:00 PM",
        "friday": "9:00 AM - 6:00 PM",
        "saturday": "12:00 PM - 6:00 PM",
        "sunday": "Closed",
    },

    "services": {
        "bath": {
            "price": 45,
            "duration_minutes": 30,
        },
        "bath_and_trim": {
            "price": 70,
            "duration_minutes": 60,
        },
        "full_groom": {
            "price": 90,
            "duration_minutes": 60,
        },
    },

    "vaccination_requirements": [
        "Rabies vaccination must be current.",
        "Dogs must be up to date on required vaccinations.",
    ],

    "breeds": {
        "accepted": "Most dog breeds",
        "special_cases": "Large or difficult-to-handle breeds may require human review."
    }
}


def get_service_duration(service_name: str) -> int:
    """Return the configured duration for a service name or alias."""

    normalized_name = service_name.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "full_grooming": "full_groom",
        "bath_and_trim": "bath_and_trim",
        "bath_trim": "bath_and_trim",
    }
    service_key = aliases.get(normalized_name, normalized_name)
    service = BUSINESS_INFO["services"].get(service_key)

    if not service:
        raise ValueError(f"Unknown grooming service: {service_name}")

    return service["duration_minutes"]