/**
 * Apple Design & Fluid Motion Physics Engine
 * Translates WWDC Designing Fluid Interfaces algorithms into zero-dependency web primitives.
 */

/**
 * Projects the resting position of an element based on release velocity.
 * Uses Apple's exponential decay formula (Designing Fluid Interfaces WWDC 2018).
 *
 * @param initialVelocity Velocity in px/s at the moment of release
 * @param decelerationRate Rate of exponential decay (0.998 for standard scroll, 0.99 for snappy)
 * @returns Projected offset distance in px from current position
 */
export function project(
  initialVelocity: number,
  decelerationRate = 0.998
): number {
  if (Math.abs(initialVelocity) < 1) return 0;
  return ((initialVelocity / 1000) * decelerationRate) / (1 - decelerationRate);
}

/**
 * Calculates rubber-banded resistance when dragging past a boundary.
 * Apple's exact rubber-band formula from UIKit / SwiftUI.
 *
 * @param overshoot Distance past the boundary in px (positive or negative)
 * @param dimension Dimension (width or height) of the moving element / container in px
 * @param constant Resistance constant (Apple default = 0.55)
 * @returns Dampened visual offset in px
 */
export function rubberband(
  overshoot: number,
  dimension = 300,
  constant = 0.55
): number {
  if (dimension <= 0) return 0;
  const sign = overshoot < 0 ? -1 : 1;
  const absOvershoot = Math.abs(overshoot);
  const dampened =
    (absOvershoot * dimension * constant) /
    (dimension + constant * absOvershoot);
  return sign * dampened;
}

export type HapticType =
  'light' | 'medium' | 'heavy' | 'selection' | 'success' | 'warning' | 'error';

/**
 * Multimodal haptic feedback via Web Vibration API.
 * Fires instantly on the causal interaction frame with zero perceptible latency.
 */
export function triggerHaptic(type: HapticType = 'light'): void {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return;
  if (!('vibrate' in navigator) || typeof navigator.vibrate !== 'function')
    return;

  try {
    switch (type) {
      case 'selection':
        navigator.vibrate(6);
        break;
      case 'light':
        navigator.vibrate(10);
        break;
      case 'medium':
        navigator.vibrate(18);
        break;
      case 'heavy':
        navigator.vibrate(28);
        break;
      case 'success':
        navigator.vibrate([10, 40, 15]);
        break;
      case 'warning':
        navigator.vibrate([18, 50, 18]);
        break;
      case 'error':
        navigator.vibrate([24, 40, 24, 40, 32]);
        break;
      default:
        navigator.vibrate(10);
    }
  } catch {
    // Ignore unsupported browser environments gracefully
  }
}

/**
 * Calculates instant pointer velocity from recent movement history.
 */
export interface PointerVelocityTracker {
  addPoint: (x: number, y: number, time?: number) => void;
  getVelocity: () => { vx: number; vy: number };
  reset: () => void;
}

export function createVelocityTracker(): PointerVelocityTracker {
  const history: Array<{ x: number; y: number; t: number }> = [];
  const maxHistoryMs = 100; // Track last 100ms for accurate release velocity

  return {
    addPoint(x: number, y: number, time = Date.now()) {
      history.push({ x, y, t: time });
      // Prune old history entries
      const cutoff = time - maxHistoryMs;
      while (history.length > 2 && history[0].t < cutoff) {
        history.shift();
      }
    },
    getVelocity() {
      if (history.length < 2) return { vx: 0, vy: 0 };
      const first = history[0];
      const last = history[history.length - 1];
      const dt = (last.t - first.t) / 1000;
      if (dt <= 0.001) return { vx: 0, vy: 0 };
      return {
        vx: (last.x - first.x) / dt,
        vy: (last.y - first.y) / dt,
      };
    },
    reset() {
      history.length = 0;
    },
  };
}
