export interface CalendarEventInput {
  title: string;
  description?: string;
  location?: string;
  startDate: Date;
  endDate: Date;
}

export function generateICS(events: CalendarEventInput[]): string {
  const formatDate = (d: Date): string => {
    return d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
  };

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//KL Sync//ERP Timetable Calendar//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
  ];

  for (const event of events) {
    lines.push('BEGIN:VEVENT');
    lines.push(`SUMMARY:${event.title.replace(/\n/g, ' ')}`);
    if (event.description) {
      lines.push(`DESCRIPTION:${event.description.replace(/\n/g, ' ')}`);
    }
    if (event.location) {
      lines.push(`LOCATION:${event.location.replace(/\n/g, ' ')}`);
    }
    lines.push(`DTSTART:${formatDate(event.startDate)}`);
    lines.push(`DTEND:${formatDate(event.endDate)}`);
    lines.push(`DTSTAMP:${formatDate(new Date())}`);
    lines.push(`UID:${Math.random().toString(36).substring(2)}@kl-sync`);
    lines.push('END:VEVENT');
  }

  lines.push('END:VCALENDAR');
  return lines.join('\r\n');
}

export function downloadICSFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/calendar;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
