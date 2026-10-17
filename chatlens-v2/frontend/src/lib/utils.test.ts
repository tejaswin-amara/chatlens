import { test, describe } from 'node:test';
import assert from 'node:assert';
import { cn } from './utils';

describe('Zero-dependency cn() helper', () => {
  test('joins simple string class names', () => {
    assert.strictEqual(cn('foo', 'bar', 'baz'), 'foo bar baz');
  });

  test('filters out falsy values (false, null, undefined, 0, "")', () => {
    assert.strictEqual(
      cn('foo', false, null, undefined, 0, '', 'bar'),
      'foo bar'
    );
  });

  test('handles object conditionals', () => {
    assert.strictEqual(
      cn('base', { active: true, disabled: false, highlighted: true }),
      'base active highlighted'
    );
  });

  test('handles nested arrays', () => {
    assert.strictEqual(cn(['foo', ['bar', false, ['baz']]]), 'foo bar baz');
  });

  test('handles mixed strings, numbers, arrays, and objects', () => {
    assert.strictEqual(
      cn(
        'flex',
        ['items-center', { 'justify-between': true, hidden: false }],
        'p-4'
      ),
      'flex items-center justify-between p-4'
    );
  });
});
