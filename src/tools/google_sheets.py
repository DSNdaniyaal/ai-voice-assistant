import os
from datetime import datetime

from dotenv import load_dotenv
from googleapiclient.discovery import build

from src.services.google_service import get_google_credentials

load_dotenv()

SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")

SHEET_NAME = "Grooming Log"

SHEET_RANGE = f"'{SHEET_NAME}'!A:L"

HEADERS = [
    "customer_id",
    "name",
    "phone",
    "dog_name",
    "notes",
    "last_call",
    "timestamp",
    "intent",
    "outcome",
    "summary",
    "handoff",
    "calendar_event_link",
]


def get_sheets_service():
    credentials = get_google_credentials()

    return build(
        "sheets",
        "v4",
        credentials=credentials,
    )


def record_customer_interaction(
    phone: str,
    name: str = "",
    dog_name: str = "",
    intent: str = "",
    outcome: str = "",
    summary: str = "",
    notes: str = "",
    handoff: str = "no",
    calendar_event_link: str = "",
    timestamp: str | None = None,
    customer_id: str | None = None,
):
    """
    Record one customer interaction in the Grooming Log sheet.
    """

    if not SPREADSHEET_ID:
        raise ValueError(
            "GOOGLE_SPREADSHEET_ID is not configured in .env"
        )

    service = get_sheets_service()

    rows = _get_rows(
        service,
        SPREADSHEET_ID,
    )

    existing_customer = _find_customer(
        rows,
        phone,
    )

    if customer_id:
        final_customer_id = customer_id

    elif existing_customer:
        final_customer_id = existing_customer[0]

    else:
        final_customer_id = _next_customer_id(rows)

    row = [
        final_customer_id,
        name,
        phone,
        dog_name,
        notes,
        _today(),
        timestamp or _timestamp(),
        intent,
        outcome,
        summary,
        handoff,
        _calendar_link_formula(calendar_event_link),
    ]

    return (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=SPREADSHEET_ID,
            range=SHEET_RANGE,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={
                "values": [row]
            },
        )
        .execute()
    )


def _get_rows(
    service,
    spreadsheet_id: str,
) -> list[list[str]]:
    """
    Get all rows from the Grooming Log sheet.
    Creates the sheet and headers if necessary.
    """

    _ensure_sheet(
        service,
        spreadsheet_id,
    )

    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=SHEET_RANGE,
        )
        .execute()
    )

    rows = result.get("values", [])

    if rows:
        if rows[0] != HEADERS:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{SHEET_NAME}'!A1:L1",
                valueInputOption="RAW",
                body={
                    "values": [HEADERS]
                },
            ).execute()
        return rows

    # Sheet exists but is empty.
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{SHEET_NAME}'!A1:L1",
        valueInputOption="RAW",
        body={
            "values": [HEADERS]
        },
    ).execute()

    return [HEADERS]


def _calendar_link_formula(url: str) -> str:
    """Return a clickable Sheets formula for a Calendar event URL."""

    if not url:
        return ""

    escaped_url = url.replace('"', '""')
    return f'=HYPERLINK("{escaped_url}","Open calendar event")'


def _ensure_sheet(
    service,
    spreadsheet_id: str,
) -> None:
    """
    Create Grooming Log tab if it doesn't exist.
    """

    result = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties.title",
        )
        .execute()
    )

    sheets = result.get("sheets", [])

    exists = any(
        sheet.get("properties", {}).get("title") == SHEET_NAME
        for sheet in sheets
    )

    if exists:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": SHEET_NAME
                        }
                    }
                }
            ]
        },
    ).execute()


def _find_customer(
    rows: list[list[str]],
    phone: str,
) -> list[str] | None:
    """
    Find the first customer whose phone number matches.
    """

    for row in rows[1:]:
        if len(row) > 2 and row[2] == phone:
            return row

    return None


def _next_customer_id(
    rows: list[list[str]],
) -> str:
    """
    Generate the next customer ID.

    Example:
        001
        002
        003
    """

    ids = {
        row[0]
        for row in rows[1:]
        if row and row[0]
    }

    next_id = 1

    while f"{next_id:03d}" in ids:
        next_id += 1

    return f"{next_id:03d}"


def _today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(
        timespec="minutes"
    )