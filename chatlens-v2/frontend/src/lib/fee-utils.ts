/**
 * Fee calculation and parsing utilities for ERP fee tables.
 */

/**
 * Safely parses currency values into clean float numbers.
 * Handles ₹, $, €, £, ¥, commas, spaces, currency text ('INR', 'Rs', 'USD', etc.),
 * and accounting parens: (1,500.00) -> -1500.
 */
export function parseCurrency(val: unknown): number {
  if (val === null || val === undefined || typeof val === 'boolean') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;

  let str = String(val).trim();
  if (!str || /^(n\/a|nil|none|null|undefined|-)$/i.test(str)) return 0;

  const isNegative =
    /^\(.*\)$/.test(str) || /^-\s*\d/.test(str.replace(/^[^\d-]*/, ''));
  str = str.replace(/\/-\s*$/, '').replace(/,/g, '');
  const match = str.match(/\d+(?:\.\d+)?/);
  if (!match) return 0;

  const parsed = parseFloat(match[0]);
  if (isNaN(parsed)) return 0;

  return isNegative ? -parsed : parsed;
}

/**
 * Normalizes header keys by lowercasing, stripping duplicate suffix (_1, _2), and trimming.
 */
function normalizeKey(key: string): string {
  return key.toLowerCase().replace(/_\d+$/, '').trim();
}

/**
 * Dynamically finds the status column key using priority fuzzy matching
 * while excluding payment date/method/mode/ref/receipt/txn columns.
 */
export function findStatusKey(
  row: Record<string, unknown>
): string | undefined {
  if (!row || typeof row !== 'object') return undefined;

  const keys = Object.keys(row);

  const nonStatusPayKeywords = [
    'date',
    'method',
    'mode',
    'id',
    'ref',
    'type',
    'name',
    'number',
    'txn',
    'transaction',
    'receipt',
    'bank',
    'gateway',
    'time',
    'by',
    'to',
    'from',
    'chq',
    'cheque',
    'dd',
    'upi',
    'utr',
    'portal',
    'payer',
    'payee',
  ];

  // Priority 1: Explicit status/state columns
  const p1 = keys.find((k) => {
    const norm = normalizeKey(k);
    return (
      norm === 'payment status' ||
      norm === 'pay status' ||
      norm === 'fee status' ||
      norm === 'due status' ||
      norm === 'payment state' ||
      norm === 'fee state' ||
      norm.includes('payment status') ||
      norm.includes('pay status') ||
      norm.includes('fee status') ||
      norm.includes('due status')
    );
  });
  if (p1) return p1;

  // Priority 2: Generic status or state
  const p2 = keys.find((k) => {
    const norm = normalizeKey(k);
    if (
      norm === 'status' ||
      norm === 'state' ||
      norm.includes('status') ||
      norm.includes('state')
    ) {
      return true;
    }
    if (norm.includes('pay')) {
      return !nonStatusPayKeywords.some((ex) => norm.includes(ex));
    }
    return false;
  });
  if (p2) return p2;

  // Priority 3: Fallback to remarks or condition
  return keys.find((k) => {
    const norm = normalizeKey(k);
    return norm.includes('remark') || norm.includes('condition');
  });
}

/**
 * Finds explicit due / balance column key (Tier 1).
 */
function findExplicitDueKey(row: Record<string, unknown>): string | undefined {
  if (!row || typeof row !== 'object') return undefined;

  const keys = Object.keys(row);

  const exclusionKeywords = [
    'paid',
    'received',
    'concession',
    'scholarship',
    'discount',
    'waived',
    'waiver',
    'refund',
    'date',
    'id',
    'type',
    'name',
    'head',
    'desc',
    'description',
    'sl',
    'no',
    'code',
    's.no',
    'sn',
    'remarks',
    'status',
    'mode',
    'method',
    'receipt',
    'ref',
    'txn',
  ];

  const tier1Patterns = [
    'amount due',
    'due amount',
    'balance due',
    'balance amount',
    'unpaid amount',
    'payable amount',
    'pending amount',
    'balance',
    'due',
    'pending',
    'unpaid',
    'payable',
    'outstanding',
  ];

  for (const pattern of tier1Patterns) {
    const match = keys.find((k) => {
      const norm = normalizeKey(k);
      if (exclusionKeywords.some((ex) => norm.includes(ex))) return false;
      return norm === pattern || norm.includes(pattern);
    });
    if (match) return match;
  }

  return undefined;
}

/**
 * Dynamically finds the due/balance amount column key using priority fuzzy matching
 * while excluding paid/concession/scholarship/date/id columns.
 * Prioritizes explicit due/balance columns (Tier 1) over gross fee/total columns (Tier 2).
 */
function findDueAmountKey(row: Record<string, unknown>): string | undefined {
  if (!row || typeof row !== 'object') return undefined;

  const explicit = findExplicitDueKey(row);
  if (explicit) return explicit;

  const keys = Object.keys(row);
  const exclusionKeywords = [
    'paid',
    'received',
    'concession',
    'scholarship',
    'discount',
    'waived',
    'waiver',
    'refund',
    'date',
    'id',
    'type',
    'name',
    'head',
    'desc',
    'description',
    'sl',
    'no',
    'code',
    's.no',
    'sn',
    'remarks',
    'status',
    'mode',
    'method',
    'receipt',
    'ref',
    'txn',
  ];

  // Priority Tier 2: Fallback to generic amount / fee / total (only if Tier 1 is absent)
  const tier2Patterns = [
    'total due',
    'net due',
    'net amount',
    'amount',
    'fee amount',
    'total amount',
    'gross fee',
    'total fee',
    'fee',
    'total',
    'grand total',
  ];

  for (const pattern of tier2Patterns) {
    const match = keys.find((k) => {
      const norm = normalizeKey(k);
      if (exclusionKeywords.some((ex) => norm.includes(ex))) return false;
      return norm === pattern || norm.includes(pattern);
    });
    if (match) return match;
  }

  return undefined;
}

/**
 * Detects summary or total rows (e.g. "Total", "Grand Total", "Subtotal").
 */
export function isSummaryRow(row: Record<string, unknown>): boolean {
  if (!row || typeof row !== 'object') return false;

  const summaryKeywords = [
    'total',
    'grand total',
    'subtotal',
    'sub-total',
    'sub total',
    'sum',
    'overall',
    'net total',
  ];

  return Object.values(row).some((val) => {
    if (typeof val === 'string') {
      const vNorm = val.toLowerCase().trim();
      if (summaryKeywords.includes(vNorm)) return true;
      return summaryKeywords.some(
        (k) => vNorm.startsWith(`${k} `) || vNorm.startsWith(`${k}:`)
      );
    }
    return false;
  });
}

/**
 * Determines whether a row represents an unpaid or pending fee item.
 */
export function isRowUnpaid(row: Record<string, unknown>): boolean {
  if (!row || typeof row !== 'object') return false;
  if (isSummaryRow(row)) return false;

  const statusKey = findStatusKey(row);
  const explicitDueKey = findExplicitDueKey(row);
  const fallbackDueKey = findDueAmountKey(row);

  const unpaidStatusKeywords = [
    'unpaid',
    'pending',
    'due',
    'partial',
    'partially paid',
    'partially',
    'not paid',
    'not-paid',
    'waiting',
    'overdue',
    'awaiting',
    'un-paid',
    'un paid',
  ];

  const paidStatusKeywords = [
    'paid',
    'completed',
    'cleared',
    'settled',
    'nil',
    'full',
    'fully paid',
  ];

  if (statusKey && row[statusKey] !== undefined && row[statusKey] !== null) {
    const statusVal = String(row[statusKey]).toLowerCase().trim();

    const matchesUnpaid = unpaidStatusKeywords.some((kw) =>
      statusVal.includes(kw)
    );
    if (matchesUnpaid) return true;

    const matchesPaid =
      paidStatusKeywords.some((kw) => statusVal.includes(kw)) &&
      !statusVal.includes('partially') &&
      !statusVal.includes('partial') &&
      !statusVal.includes('not') &&
      !statusVal.includes('un');

    if (matchesPaid) {
      const paidKey = Object.keys(row).find((k) => {
        const norm = normalizeKey(k);
        return (
          (norm.includes('paid') ||
            norm.includes('receipt') ||
            norm.includes('received') ||
            norm.includes('cleared') ||
            norm.includes('credited')) &&
          !norm.includes('unpaid') &&
          !norm.includes('status') &&
          !norm.includes('date')
        );
      });
      const balanceKey = Object.keys(row).find((k) => {
        const norm = normalizeKey(k);
        return (
          norm.includes('balance') ||
          norm.includes('pending') ||
          norm.includes('remaining')
        );
      });

      if (balanceKey) {
        return parseCurrency(row[balanceKey]) > 0;
      }
      if (paidKey && explicitDueKey) {
        const total = parseCurrency(row[explicitDueKey]);
        const paid = parseCurrency(row[paidKey]);
        if (total > 0 && paid >= total) return false;
      }
      return false;
    }
  }

  // If status key is absent/blank
  if (explicitDueKey) {
    return parseCurrency(row[explicitDueKey]) > 0;
  }

  // If fallback gross fee key exists, check if paid column exists and compare
  const paidKey = Object.keys(row).find((k) => {
    const norm = normalizeKey(k);
    return (
      (norm.includes('paid') ||
        norm.includes('receipt') ||
        norm.includes('received') ||
        norm.includes('cleared') ||
        norm.includes('credited')) &&
      !norm.includes('unpaid') &&
      !norm.includes('status') &&
      !norm.includes('date')
    );
  });

  if (fallbackDueKey && paidKey) {
    const total = parseCurrency(row[fallbackDueKey]);
    const paid = parseCurrency(row[paidKey]);
    if (total > 0 && paid >= total) {
      return false;
    }
    if (total > 0 && total - paid > 0) {
      return true;
    }
    return false;
  }

  // Without an explicit due/balance column, explicit unpaid status, or paid vs total mismatch,
  // historical fee orders/receipts are NOT unpaid items.
  return false;
}

/**
 * Calculates pending fee amount for a single row.
 */
function getPendingAmountForRow(row: Record<string, unknown>): number {
  const balanceKey = Object.keys(row).find((k) => {
    const norm = normalizeKey(k);
    return (
      norm.includes('balance') ||
      norm.includes('pending') ||
      norm.includes('remaining')
    );
  });
  if (balanceKey) {
    const bal = parseCurrency(row[balanceKey]);
    return bal > 0 ? bal : 0;
  }

  const dueKey = findExplicitDueKey(row) || findDueAmountKey(row);
  if (!dueKey) return 0;

  const total = parseCurrency(row[dueKey]);
  if (total <= 0) return 0;

  const paidKey = Object.keys(row).find((k) => {
    const norm = normalizeKey(k);
    return (
      (norm.includes('paid') ||
        norm.includes('receipt') ||
        norm.includes('received') ||
        norm.includes('cleared') ||
        norm.includes('credited')) &&
      !norm.includes('unpaid') &&
      !norm.includes('status') &&
      !norm.includes('date')
    );
  });

  if (paidKey) {
    const paid = parseCurrency(row[paidKey]);
    const rem = total - paid;
    return rem > 0 ? rem : 0;
  }

  return total;
}

/**
 * Calculates total pending fee due from array of ERP fee rows.
 */
export function calculatePendingFee(data: Record<string, unknown>[]): number {
  if (!Array.isArray(data) || data.length === 0) {
    return 0;
  }

  const detailRows = data.filter((row) => !isSummaryRow(row));
  const rowsToProcess = detailRows.length > 0 ? detailRows : data;

  return rowsToProcess.reduce((sum, row) => {
    if (isRowUnpaid(row)) {
      const amt = getPendingAmountForRow(row);
      return sum + amt;
    }
    return sum;
  }, 0);
}
