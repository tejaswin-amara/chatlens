import test from 'node:test';
import assert from 'node:assert';
import {
  parseCurrency,
  findStatusKey,
  isSummaryRow,
  isRowUnpaid,
  calculatePendingFee,
} from './fee-utils';

test('parseCurrency handles various currency formats, symbols, and accounting parens', () => {
  assert.strictEqual(parseCurrency('₹15,000.00'), 15000);
  assert.strictEqual(parseCurrency('$1,500.50'), 1500.5);
  assert.strictEqual(parseCurrency('INR 2,500'), 2500);
  assert.strictEqual(parseCurrency('Rs. 500/-'), 500);
  assert.strictEqual(parseCurrency('(₹1,500.00)'), -1500);
  assert.strictEqual(parseCurrency('-500'), -500);
  assert.strictEqual(parseCurrency('N/A'), 0);
  assert.strictEqual(parseCurrency(null), 0);
  assert.strictEqual(parseCurrency(undefined), 0);
  assert.strictEqual(parseCurrency(1234.56), 1234.56);
});

test('findStatusKey locates status columns accurately', () => {
  assert.strictEqual(
    findStatusKey({ 'Payment Status': 'PAID', Amount: '1000' }),
    'Payment Status'
  );
  assert.strictEqual(
    findStatusKey({ Status: 'PENDING', Amount: '1000' }),
    'Status'
  );
  assert.strictEqual(findStatusKey({ Remarks: 'Unpaid fee order' }), 'Remarks');
});

test('isSummaryRow identifies summary or total rows', () => {
  assert.strictEqual(
    isSummaryRow({ 'Fee Head': 'Total', Amount: '50000' }),
    true
  );
  assert.strictEqual(
    isSummaryRow({ 'Fee Head': 'Grand Total:', Amount: '50000' }),
    true
  );
  assert.strictEqual(
    isSummaryRow({ 'Fee Head': 'Tuition Fee', Amount: '50000' }),
    false
  );
});

test('isRowUnpaid and calculatePendingFee correctly compute pending amounts', () => {
  const feeRows = [
    {
      'Fee Type': 'Tuition Fee',
      'Amount Due': '150,000',
      'Paid Amount': '150,000',
      Status: 'PAID',
    },
    {
      'Fee Type': 'Special Skill Fee',
      'Amount Due': '15,000',
      'Paid Amount': '10,000',
      Status: 'PARTIALLY PAID',
    },
    {
      'Fee Type': 'Exam Fee',
      'Amount Due': '2,500',
      'Paid Amount': '0',
      Status: 'UNPAID',
    },
    {
      'Fee Type': 'Total',
      'Amount Due': '167,500',
      'Paid Amount': '160,000',
      Status: 'SUMMARY',
    },
  ];

  assert.strictEqual(isRowUnpaid(feeRows[0]), false);
  assert.strictEqual(isRowUnpaid(feeRows[1]), true);
  assert.strictEqual(isRowUnpaid(feeRows[2]), true);
  assert.strictEqual(isRowUnpaid(feeRows[3]), false);

  // Expected pending: 5,000 (from 15000 - 10000) + 2,500 = 7,500
  const totalPending = calculatePendingFee(feeRows);
  assert.strictEqual(totalPending, 7500);
});
