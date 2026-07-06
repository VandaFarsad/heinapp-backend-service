import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from types import TracebackType
from typing import Any, Optional, Self

import icalendar
from caldav import Calendar, DAVClient, Event
from caldav.davclient import get_davclient
from dateutil.parser import parse
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CalDAVEvent:
    """Typed representation of a CalDAV calendar event.

    Immutable value object returned by CalDAVService methods. Provides
    conversion methods for database persistence and API serialization,
    replacing raw dict returns.
    """

    uid: str
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    location: str
    url: str
    all_day: bool
    recurrence_id: str | None = None
    rrule: str | None = None
    exdate: str | None = None

    def to_model_fields(self) -> dict[str, Any]:
        """Convert to CalendarEvent model field dictionary.

        Returns fields ready for CalendarEvent creation or update,
        excluding uid and recurrence_id (used as lookup keys separately).

        Example:
            >>> CalendarEvent.objects.update_or_create(
                    uid=event.uid,
                    recurrence_id=event.recurrence_id,
                    defaults=event.to_model_fields()
                )
        """
        return {
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "location": self.location,
            "url": self.url,
            "all_day": self.all_day,
            "rrule": self.rrule,
            "exdate": self.exdate,
        }

    def to_response_dict(self) -> dict[str, Any]:
        """Serialize for JSON API response.

        Converts datetime fields to ISO 8601 strings for JSON compatibility.
        """
        return {
            "uid": self.uid,
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "location": self.location,
            "url": self.url,
            "all_day": self.all_day,
            "rrule": self.rrule,
            "exdate": self.exdate,
        }


class CalDAVService:
    """Service class for interacting with a CalDAV calendar server.

    This class provides a comprehensive interface for CalDAV operations including
    fetching, creating, updating, and deleting calendar events. It manages server
    authentication, iCalendar content generation/parsing, and handles timezone
    conversions for Django-based applications.

    The service should be used as a context manager to ensure proper connection
    cleanup. Configuration is loaded from Django settings.CALDAV_CONFIG.

    Attributes:
        config: CalDAV server configuration from Django settings.
        client: DAVClient instance for server communication.
        calendar: Calendar object representing the connected calendar.

    Examples:
        Fetch events for a date range:
            >>> with CalDAVService() as service:
            >>>     events = service.get_events(start_date, end_date)

        Create a new event:
            >>> with CalDAVService() as service:
            >>>     event_data = {
            >>>         "title": "Meeting",
            >>>         "start_date": "2026-02-22T10:00:00Z",
            >>>         "end_date": "2026-02-22T11:00:00Z",
            >>>         "description": "Team sync",
            >>>         "location": "Conference Room A"
            >>>     }
            >>>     new_event = service.create_event(event_data)

        Update an existing event:
            >>> with CalDAVService() as service:
            >>>     updated = service.update_event(uid, updated_data)

        Delete an event:
            >>> with CalDAVService() as service:
            >>>     success = service.delete_event(uid)

    Raises:
        ValueError: If calendar connection is not established.
        Exception: For CalDAV server communication errors.
    """

    def __init__(
        self,
        *,
        config: Optional[dict[str, Any]] = None,
        client: Optional[DAVClient] = None,
        calendar: Optional[Calendar] = None,
    ) -> None:
        """Initialize CalDAV service with optional dependency injection.

        When called without arguments, connects eagerly to the CalDAV server.
        When client and calendar are provided (e.g. in tests), skips connection.

        Args:
            config: Optional dictionary with CalDAV configuration (for testing or custom settings).
            client: Pre-configured DAVClient instance (for testing).
            calendar: Pre-configured Calendar instance (for testing).

        Raises:
            Exception: If connection to CalDAV server fails (when not injected).
        """
        self.config: dict[str, Any] = config or settings.CALDAV_CONFIG
        self.client: Optional[DAVClient] = client
        self.calendar: Optional[Calendar] = calendar
        if not self.calendar:
            self._connect()

    def _connect(self) -> None:
        """Establish connection to CalDAV server.

        Creates a DAVClient instance using configuration settings and discovers
        the calendar collection via CalDAV principal. If CALDAV_CALENDAR_NAME
        is set, uses that specific calendar; otherwise uses the first available.

        Raises:
            Exception: If authentication fails or no calendar is found.
        """
        try:
            # Only pass connection-related keys to get_davclient
            client_kwargs = {
                "url": self.config["url"],
                "username": self.config["username"],
                "password": self.config["password"],
            }
            calendar_url = self.config["calendar_url"]

            self.client = get_davclient(**client_kwargs)
            self.calendar = Calendar(client=self.client, url=calendar_url)
            if self.calendar is None:
                raise ValueError("Specified calendar not found on the CalDAV server")

            logger.info(f"Connected to calendar: {self.calendar.name} ({self.calendar.url})")

        except Exception as e:
            logger.error(f"CalDAV connection failed: {e}", exc_info=True)
            self.client = None
            self.calendar = None
            raise

    def __enter__(self) -> Self:
        """Context manager entry.

        Returns:
            Self: The CalDAVService instance for context management.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[BaseException] = None,
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> None:
        """Context manager exit and cleanup.

        Closes the CalDAV client connection and cleans up resources.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_value: Exception instance if an exception was raised.
            traceback: Traceback object if an exception was raised.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.calendar = None

    def get_events(self, start_date: datetime | None = None, end_date: datetime | None = None) -> list[CalDAVEvent]:
        """Fetch calendar events from CalDAV server within a date range.

        Retrieves master events only (not expanded instances) from the connected calendar.
        Recurring events are returned with their RRULE, and expansion is handled by the frontend.
        If no dates are provided, defaults to current month through end of next month.

        Args:
            start_date: Start of date range (inclusive). Defaults to first day
                of current month if not provided.
            end_date: End of date range (exclusive). Defaults to first day of
                month after next if not provided.

        Returns:
            List of CalDAVEvent instances (master events only). Returns empty list if calendar
            is not connected or on error.
        """
        try:
            if not self.calendar:
                return []

            # Default to current month if no dates provided
            if not start_date:
                now = datetime.now(timezone.utc)
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            if not end_date:
                # End of next month (use timedelta to avoid month overflow)
                # Jump ~62 days ahead, then snap to 1st of that month
                approx = start_date + timedelta(days=62)
                end_date = approx.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Get master events only (expand=False) - frontend will handle recurrence expansion
            master_events: list[Event] = self.calendar.search(start=start_date, end=end_date, expand=False)
            parsed = []

            for event in master_events:
                parsed_event = self._parse_event(event)
                if parsed_event:
                    parsed.append(parsed_event)

            return parsed

        except Exception as e:
            logger.error(f"Error fetching events: {e}", exc_info=True)
            return []

    def create_event(self, event_data: dict[str, Any]) -> CalDAVEvent:
        """Create a new calendar event on the CalDAV server.

        Generates a unique UID, creates iCalendar content, and saves the event
        to the server. Supports both all-day and timed events.

        Args:
            event_data: Dictionary containing event details:
                - title (str): Event title/summary
                - start_date (str): ISO format datetime string
                - end_date (str): ISO format datetime string
                - description (str, optional): Event description
                - location (str, optional): Event location
                - url (str, optional): Meeting/event URL
                - all_day (bool, optional): Whether event is all-day

        Returns:
            CalDAVEvent with created event data including generated UID.

        Raises:
            ValueError: If calendar is not connected.
            Exception: If event creation fails on the server.
        """
        try:
            if not self.calendar:
                raise ValueError("No calendar connected")

            event_uid = str(uuid.uuid4())

            # Convert datetime strings to datetime objects
            start_dt = self._parse_datetime(event_data["start_date"])
            end_dt = self._parse_datetime(event_data["end_date"])

            # Create iCalendar content
            ical_content = self._create_ical_content(event_uid, event_data, start_dt, end_dt)

            # Create event on server
            self.calendar.save_event(ical_content)

            return self._build_event(event_uid, event_data, start_dt, end_dt)

        except Exception as e:
            logger.error(f"Error creating event: {e}", exc_info=True)
            raise

    def update_event(self, uid: str, event_data: dict[str, Any]) -> CalDAVEvent:
        """Update an existing calendar event on the CalDAV server.

        Locates the event by UID using CalDAV's efficient event_by_uid lookup
        and updates it with new data. Preserves the original UID.

        Args:
            uid: Unique identifier of the event to update.
            event_data: Dictionary containing updated event details (same
                structure as create_event).

        Returns:
            CalDAVEvent with updated event data.

        Raises:
            ValueError: If calendar is not connected or event UID not found.
            Exception: If event update fails on the server.
        """
        try:
            if not self.calendar:
                raise ValueError("No calendar connected")

            # Efficient single-request lookup by UID
            try:
                target_event = self.calendar.event_by_uid(uid)
            except Exception:
                raise ValueError(f"Event with UID {uid} not found")

            # Update event content
            start_dt = self._parse_datetime(event_data["start_date"])
            end_dt = self._parse_datetime(event_data["end_date"])

            ical_content = self._create_ical_content(uid, event_data, start_dt, end_dt)
            target_event.data = ical_content
            target_event.save()

            return self._build_event(uid, event_data, start_dt, end_dt)

        except Exception as e:
            logger.error(f"Error updating event: {e}", exc_info=True)
            raise

    def delete_event(self, uid: str) -> bool:
        """Delete a calendar event from the CalDAV server.

        Looks up the event by UID using CalDAV's efficient event_by_uid
        and removes it from the calendar.

        Args:
            uid: Unique identifier of the event to delete.

        Returns:
            True if event was found and deleted, False if event not found.

        Raises:
            ValueError: If calendar is not connected.
            Exception: If deletion fails on the server.
        """
        try:
            if not self.calendar:
                raise ValueError("No calendar connected")

            # Efficient single-request lookup by UID
            try:
                event = self.calendar.event_by_uid(uid)
            except Exception:
                return False

            event.delete()
            return True

        except Exception as e:
            logger.error(f"Error deleting event: {e}", exc_info=True)
            raise

    def create_exception(
        self, master_uid: str, occurrence_start_str: str, event_data: dict[str, Any]
    ) -> tuple[CalDAVEvent, CalDAVEvent]:
        """Create an exception for a single occurrence of a recurring event.

        Adds EXDATE to the master event to suppress the original occurrence,
        then creates a standalone event with the modified data.

        Args:
            master_uid: UID of the master recurring event.
            occurrence_start_str: ISO 8601 string of the occurrence to replace.
            event_data: New event data for the exception occurrence.

        Returns:
            Tuple of (updated_master, exception_event).

        Raises:
            ValueError: If calendar is not connected or master event not found.
            Exception: If CalDAV operation fails.
        """
        try:
            if not self.calendar:
                raise ValueError("No calendar connected")

            updated_master = self._add_exdate_to_master(master_uid, occurrence_start_str)

            # Create standalone exception event (new UID, no RRULE)
            exception_uid = str(uuid.uuid4())
            exception_data: dict[str, Any] = {**event_data, "rrule": "", "exdate": ""}
            exception_start = self._parse_datetime(event_data["start_date"])
            exception_end = self._parse_datetime(event_data["end_date"])
            exception_ical = self._create_ical_content(exception_uid, exception_data, exception_start, exception_end)
            self.calendar.save_event(exception_ical)

            exception_event = self._build_event(exception_uid, exception_data, exception_start, exception_end)
            return updated_master, exception_event

        except Exception as e:
            logger.error(f"Error creating exception: {e}", exc_info=True)
            raise

    def delete_occurrence(self, master_uid: str, occurrence_start_str: str) -> CalDAVEvent:
        """Remove a single occurrence from a recurring event by adding EXDATE.

        Args:
            master_uid: UID of the master recurring event.
            occurrence_start_str: ISO 8601 string of the occurrence to remove.

        Returns:
            Updated master CalDAVEvent with new EXDATE.

        Raises:
            ValueError: If calendar is not connected or master event not found.
            Exception: If CalDAV operation fails.
        """
        try:
            if not self.calendar:
                raise ValueError("No calendar connected")

            return self._add_exdate_to_master(master_uid, occurrence_start_str)

        except Exception as e:
            logger.error(f"Error deleting occurrence: {e}", exc_info=True)
            raise

    def _add_exdate_to_master(self, master_uid: str, occurrence_start_str: str) -> CalDAVEvent:
        """Append an EXDATE to a master recurring event and save to CalDAV.

        Shared helper for create_exception and delete_occurrence.
        """
        try:
            master_caldav = self.calendar.event_by_uid(master_uid)
        except Exception:
            raise ValueError(f"Master event {master_uid} not found")

        master_event = self._parse_event(master_caldav)
        if not master_event:
            raise ValueError(f"Could not parse master event {master_uid}")

        occurrence_start = self._parse_datetime(occurrence_start_str)
        occ_iso = occurrence_start.isoformat()
        updated_exdate = f"{master_event.exdate},{occ_iso}" if master_event.exdate else occ_iso

        master_data: dict[str, Any] = {
            **master_event.to_model_fields(),
            "rrule": master_event.rrule or "",
            "exdate": updated_exdate,
        }
        updated_ical = self._create_ical_content(
            master_uid, master_data, master_event.start_date, master_event.end_date
        )
        master_caldav.data = updated_ical
        master_caldav.save()

        return self._build_event(master_uid, master_data, master_event.start_date, master_event.end_date)

    def _parse_event(self, caldav_event: Event) -> CalDAVEvent | None:
        """Parse CalDAV event object into a CalDAVEvent.

        Extracts event properties from iCalendar component and converts them
        to a typed CalDAVEvent. The icalendar library handles escape sequences
        automatically.

        Args:
            caldav_event: CalDAV Event object from the server.

        Returns:
            CalDAVEvent instance, or None on parsing error (filtered out
            by caller).
        """
        try:
            event_obj: icalendar.Event = caldav_event.icalendar_component

            # icalendar library decodes escape sequences automatically
            description = str(event_obj.get("DESCRIPTION", ""))

            dtstart = event_obj.get("DTSTART")
            dtend = event_obj.get("DTEND")
            if not dtstart or not dtend:
                logger.warning(f"Event missing DTSTART/DTEND: {event_obj.get('UID', 'unknown')}")
                return None

            # Extract RRULE if present
            rrule_str = None
            if event_obj.get("RRULE"):
                rrule_obj = event_obj.get("RRULE")
                # Convert vRecur to string format
                rrule_str = rrule_obj.to_ical().decode("utf-8") if hasattr(rrule_obj, "to_ical") else str(rrule_obj)

            # Extract EXDATE if present (exception dates)
            exdate_str = None
            if event_obj.get("EXDATE"):
                exdate_obj = event_obj.get("EXDATE")
                # icalendar returns vDDDLists for single EXDATE properties and
                # a list of vDDDLists for multiple EXDATE properties.  Each
                # vDDDLists stores its datetimes in .dts (list of vDDDTypes).
                items = exdate_obj if isinstance(exdate_obj, list) else [exdate_obj]
                all_dates: list[str] = []
                for item in items:
                    if hasattr(item, "dts"):
                        all_dates.extend(self._format_datetime(d.dt) for d in item.dts)
                    elif hasattr(item, "dt"):
                        all_dates.append(self._format_datetime(item.dt))
                if all_dates:
                    exdate_str = ",".join(all_dates)

            return CalDAVEvent(
                uid=str(event_obj.get("UID", "")),
                title=str(event_obj.get("SUMMARY", "")),
                description=description,
                start_date=self._to_utc_datetime(dtstart.dt),
                end_date=self._to_utc_datetime(dtend.dt),
                location=str(event_obj.get("LOCATION", "")),
                url=str(event_obj.get("URL", "")),
                all_day=type(dtstart.dt) is date,
                recurrence_id=self._format_datetime(event_obj.get("RECURRENCE-ID").dt)
                if event_obj.get("RECURRENCE-ID")
                else None,
                rrule=rrule_str,
                exdate=exdate_str,
            )
        except Exception as e:
            logger.error(f"Error parsing event: {e}", exc_info=True)
            return None

    def _build_event(self, uid: str, event_data: dict[str, Any], start_dt: datetime, end_dt: datetime) -> CalDAVEvent:
        """Build CalDAVEvent from uid, raw event data, and parsed datetimes.

        Shared helper for create_event and update_event to avoid duplicated
        return-value construction.
        """
        return CalDAVEvent(
            uid=uid,
            title=event_data.get("title", ""),
            description=event_data.get("description", ""),
            start_date=start_dt,
            end_date=end_dt,
            location=event_data.get("location", ""),
            url=event_data.get("url", ""),
            all_day=event_data.get("all_day", False),
            rrule=event_data.get("rrule", ""),
            exdate=event_data.get("exdate", ""),
        )

    def _to_utc_datetime(self, dt: datetime | date) -> datetime:
        """Convert date or datetime to timezone-aware UTC datetime.

        For all-day events (date objects), returns midnight UTC.
        For naive datetimes, assumes UTC.
        """
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)

    def _create_ical_content(self, uid: str, event_data: dict[str, Any], start_dt: datetime, end_dt: datetime) -> str:
        """Generate iCalendar (RFC 5545) formatted content string.

        Uses the icalendar library for proper escaping, folding, and RFC
        compliance. Handles both all-day and timed events.

        Args:
            uid: Unique event identifier.
            event_data: Dictionary with event properties:
                - title (str): Event summary mapped to iCal SUMMARY field.
                - description (str, optional): Detailed event description
                    mapped to iCal DESCRIPTION field.
                - location (str, optional): Physical or virtual event location
                    mapped to iCal LOCATION field.
                - url (str, optional): Associated URL (e.g. meeting link)
                    mapped to iCal URL field.
                - all_day (bool, optional): If True, DTSTART/DTEND are set as
                    date values instead of datetime, and the non-standard
                    X-FUNAMBOL-ALLDAY property is added. Defaults to False.
            start_dt: Event start datetime.
            end_dt: Event end datetime.

        Returns:
            RFC 5545 compliant iCalendar content string ready for server upload.
        """
        cal = icalendar.Calendar()
        cal.add("prodid", "-//Django CalDAV//EN")
        cal.add("version", "2.0")

        event = icalendar.Event()
        event.add("uid", uid)
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("summary", event_data.get("title", ""))

        if event_data.get("description"):
            event.add("description", event_data["description"])
        if event_data.get("location"):
            event.add("location", event_data["location"])
        if event_data.get("url"):
            event.add("url", event_data["url"])

        all_day = event_data.get("all_day", False)
        if all_day:
            event.add("dtstart", start_dt.date())
            event.add("dtend", end_dt.date())
            event.add("x-funambol-allday", "1")
        else:
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)

        # Add RRULE if present
        if event_data.get("rrule"):
            try:
                # Parse RRULE string and add to event
                rrule_str = event_data["rrule"]
                event.add("rrule", icalendar.vRecur.from_ical(rrule_str))
            except Exception as e:
                logger.warning(f"Failed to parse RRULE '{event_data.get('rrule')}': {e}")

        # Add EXDATE if present (exception dates for recurring events)
        if event_data.get("exdate"):
            try:
                # Parse comma-separated exception dates
                exdate_str = event_data["exdate"]
                exdates = [self._parse_datetime(d.strip()) for d in exdate_str.split(",") if d.strip()]
                if exdates:
                    for exdate in exdates:
                        event.add("exdate", exdate)
            except Exception as e:
                logger.warning(f"Failed to parse EXDATE '{event_data.get('exdate')}': {e}")

        cal.add_component(event)
        return str(cal.to_ical().decode("utf-8"))

    def _parse_datetime(self, dt_input: str | datetime) -> datetime:
        """Parse datetime string or object into a timezone-aware datetime object.

        Accepts both string and datetime inputs for flexibility. Uses
        dateutil.parser for strings. Ensures all returned datetimes are
        timezone-aware (UTC if naive).

        Args:
            dt_input: ISO format datetime string or datetime object.

        Returns:
            Timezone-aware datetime object in UTC.
        """
        if isinstance(dt_input, datetime):
            dt = dt_input
        else:
            dt = parse(dt_input)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _format_datetime(self, dt: datetime | date | None) -> str:
        """Format datetime or date object to ISO 8601 string.

        Converts datetime objects to UTC and formats as ISO string for
        consistent API responses. Handles both timezone-aware and naive
        datetimes, as well as date-only objects.

        Args:
            dt: datetime, date object, or None to format.

        Returns:
            ISO 8601 formatted string. Empty string if dt is None.
        """
        if dt is None:
            return ""
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat()
        elif hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)
