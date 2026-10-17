export type ClassValue =
  | string
  | number
  | bigint
  | boolean
  | undefined
  | null
  | ClassValue[]
  | { [key: string]: unknown };

export function cn(...inputs: ClassValue[]): string {
  const classes: string[] = [];

  function parseInput(input: ClassValue) {
    if (!input) return;

    if (
      typeof input === 'string' ||
      typeof input === 'number' ||
      typeof input === 'bigint'
    ) {
      classes.push(String(input));
    } else if (Array.isArray(input)) {
      for (const item of input) {
        parseInput(item);
      }
    } else if (typeof input === 'object') {
      for (const [key, value] of Object.entries(input)) {
        if (value) {
          classes.push(key);
        }
      }
    }
  }

  for (const input of inputs) {
    parseInput(input);
  }

  return classes.join(' ');
}

export function exportTableToCSV(
  data: Record<string, unknown>[],
  filename: string
) {
  if (typeof window === 'undefined') return;
  if (!data || data.length === 0) return;

  const headers = Object.keys(data[0]);
  const csvRows = [headers.join(',')];

  for (const row of data) {
    const values = headers.map((header) => {
      const val = String(row[header] ?? '');
      return '"' + val.replace(/"/g, '""') + '"';
    });
    csvRows.push(values.join(','));
  }

  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('hidden', '');
  a.setAttribute('href', url);
  a.setAttribute('download', filename);
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => window.URL.revokeObjectURL(url), 100);
}
