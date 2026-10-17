import test from 'node:test';
import assert from 'node:assert/strict';
import { generateICS } from './calendar-export';

test('generateICS creates valid iCalendar output string', () => {
  const events = [
    {
      title: 'Operating Systems Lecture',
      location: 'C-301',
      description: 'Faculty: Dr. Smith',
      startDate: new Date('2026-09-01T09:00:00Z'),
      endDate: new Date('2026-09-01T10:00:00Z'),
    },
  ];

  const ics = generateICS(events);
  assert.ok(ics.includes('BEGIN:VCALENDAR'));
  assert.ok(ics.includes('BEGIN:VEVENT'));
  assert.ok(ics.includes('SUMMARY:Operating Systems Lecture'));
  assert.ok(ics.includes('LOCATION:C-301'));
  assert.ok(ics.includes('END:VEVENT'));
  assert.ok(ics.includes('END:VCALENDAR'));
});
