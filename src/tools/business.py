from typing import Any

from config import BUSINESS_INFO


def get_business_info(topic: str = "") -> dict[str, Any]:
	"""Return the single business's information for the receptionist."""
	if not topic:
		return BUSINESS_INFO
	topic_lower = topic.lower()
	return {
		key: value
		for key, value in BUSINESS_INFO.items()
		if topic_lower in key.lower()
	} or BUSINESS_INFO
