import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getRenderSpec, prepareAAForCopy, copyHTML } from '../lib/render-contract.ts';

test('copy preserves internal spaces, blank rows and glyphs; never duplicates columns', () => {
  const input = '\r\n  A   B  \r\n\r\n    / \\  \r\n';
  assert.equal(prepareAAForCopy(input), 'A   B\n\n  / \\');
  assert.equal(prepareAAForCopy('  '), '');
});

test('profile affects layout contract, not the copied text', () => {
  const code = getRenderSpec('monospace');
  const notes = getRenderSpec('notes_docs');
  assert.equal(code.cell_width, notes.cell_width);
  assert.equal(code.cell_height, 24);
  assert.equal(notes.cell_height, 30);
  assert.equal(code.baseline, 19);
  assert.equal(notes.baseline, 22);
  const aa = 'A  &B\n <_/>';
  for (const spec of [code, notes]) {
    const html = copyHTML(aa, spec);
    assert.ok(html.includes('A&nbsp;&nbsp;&amp;B<br>&nbsp;&lt;_/&gt;'));
    assert.ok(html.includes(`line-height:${spec.cell_height/spec.font_size}`));
    assert.ok(html.includes('white-space:pre'));
  }
});
