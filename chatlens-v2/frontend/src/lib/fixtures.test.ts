import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEMO_SESSION,
  DEMO_ATTENDANCE,
  DEMO_TIMETABLE_RAW,
  DEMO_MARKS,
  DEMO_FEE_ITEMS,
  DEMO_PROFILE,
  DEMO_CGPA,
  DEMO_CAPTCHA_SVG,
  DEMO_LOGIN_RESULT,
} from '@/lib/fixtures';

test('fixtures exports all 9 expected fallback datasets', () => {
  assert.ok(DEMO_SESSION, 'DEMO_SESSION must be defined');
  assert.strictEqual(DEMO_SESSION.csrfToken, 'demo_csrf_token_123');

  assert.ok(Array.isArray(DEMO_ATTENDANCE), 'DEMO_ATTENDANCE must be an array');
  assert.strictEqual(DEMO_ATTENDANCE.length, 4);
  assert.strictEqual(DEMO_ATTENDANCE[0]['Course Code'], '23CS2101R');

  assert.ok(
    Array.isArray(DEMO_TIMETABLE_RAW),
    'DEMO_TIMETABLE_RAW must be an array'
  );
  assert.strictEqual(DEMO_TIMETABLE_RAW.length, 5);

  assert.ok(Array.isArray(DEMO_MARKS), 'DEMO_MARKS must be an array');
  assert.strictEqual(DEMO_MARKS.length, 4);

  assert.ok(Array.isArray(DEMO_FEE_ITEMS), 'DEMO_FEE_ITEMS must be an array');
  assert.strictEqual(DEMO_FEE_ITEMS.length, 3);

  assert.ok(DEMO_PROFILE, 'DEMO_PROFILE must be defined');
  assert.strictEqual(DEMO_PROFILE.universityId, '2100030000');

  assert.ok(Array.isArray(DEMO_CGPA), 'DEMO_CGPA must be an array');
  assert.strictEqual(DEMO_CGPA[0].CGPA, '9.15');

  assert.ok(
    typeof DEMO_CAPTCHA_SVG === 'string',
    'DEMO_CAPTCHA_SVG must be a string'
  );
  assert.ok(
    DEMO_CAPTCHA_SVG.startsWith('data:image/svg+xml;base64,'),
    'DEMO_CAPTCHA_SVG must be data URI'
  );

  assert.ok(DEMO_LOGIN_RESULT, 'DEMO_LOGIN_RESULT must be defined');
  assert.strictEqual(DEMO_LOGIN_RESULT.success, true);
  assert.strictEqual(DEMO_LOGIN_RESULT.deviceId, 'demo_device_123');
});
