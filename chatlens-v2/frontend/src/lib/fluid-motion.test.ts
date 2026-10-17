import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  project,
  rubberband,
  createVelocityTracker,
  triggerHaptic,
} from './fluid-motion';

describe('Apple Fluid Motion Physics & Algorithms', () => {
  test('project calculates momentum landing endpoints accurately', () => {
    // 0 velocity projects 0 distance
    assert.equal(project(0), 0);

    // 1000px/s flick with default decelerationRate (0.998)
    const p1 = project(1000, 0.998);
    assert.ok(p1 > 400 && p1 < 600, `Expected p1 around 499px, got ${p1}`);

    // Snappy decelerationRate (0.99) projects shorter distance
    const p2 = project(1000, 0.99);
    assert.ok(
      p2 < p1,
      'Higher deceleration should result in shorter projected distance'
    );

    // Negative flick projects negative distance
    const pNeg = project(-800, 0.998);
    assert.ok(pNeg < 0, 'Negative velocity must project negative distance');
  });

  test('rubberband applies progressive boundary resistance', () => {
    assert.equal(rubberband(0, 300), 0);

    // Past boundary, rubber-banded value is strictly less than overshoot
    const r100 = rubberband(100, 300, 0.55);
    assert.ok(
      r100 > 0 && r100 < 100,
      `Rubberband for 100px overshoot should be < 100, got ${r100}`
    );

    // Diminishing returns: doubling overshoot produces less than double output
    const r200 = rubberband(200, 300, 0.55);
    assert.ok(r200 > r100, 'Larger overshoot gives larger dampened offset');
    assert.ok(
      r200 < 2 * r100,
      'Resistance curve must be concave (progressive dampening)'
    );

    // Negative overshoot retains sign
    const rNeg = rubberband(-100, 300, 0.55);
    assert.equal(rNeg, -r100);
  });

  test('createVelocityTracker computes velocity from timestamped history', () => {
    const tracker = createVelocityTracker();
    const now = Date.now();

    tracker.addPoint(0, 0, now);
    tracker.addPoint(50, 100, now + 50); // 50ms later: dx=50 (1000px/s), dy=100 (2000px/s)

    const vel = tracker.getVelocity();
    assert.equal(Math.round(vel.vx), 1000);
    assert.equal(Math.round(vel.vy), 2000);

    tracker.reset();
    assert.deepEqual(tracker.getVelocity(), { vx: 0, vy: 0 });
  });

  test('triggerHaptic executes safely in all test & browser environments', () => {
    assert.doesNotThrow(() => {
      triggerHaptic('light');
      triggerHaptic('selection');
      triggerHaptic('success');
      triggerHaptic('warning');
      triggerHaptic('error');
    });
  });
});
