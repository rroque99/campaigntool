/**
 * Parse a UTC timestamp string from the API.
 *
 * SQLite strips timezone info, so the API may return timestamps like
 * "2026-02-16T02:30:00" without a trailing "Z". The browser's Date
 * constructor treats such strings as local time. This helper appends
 * "Z" when no timezone indicator is present so they are correctly
 * interpreted as UTC.
 */
export function parseUTC(timestamp: string): Date {
  if (!/[Z+-]\d{0,4}$/.test(timestamp)) {
    return new Date(timestamp + "Z");
  }
  return new Date(timestamp);
}
