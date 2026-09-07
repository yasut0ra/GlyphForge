import contract from './render-contract.json' with { type: 'json' };

export type CopyProfile = keyof typeof contract.profiles;

export interface RenderSpec {
  profile: CopyProfile;
  font_family: string;
  font_size: number;
  font_advance: number;
  cell_width: number;
  cell_height: number;
  baseline: number;
  version: string;
}

export function getRenderSpec(profile: CopyProfile): RenderSpec {
  return { ...contract, ...contract.profiles[profile], profile };
}

// Copy never changes columns. Internal blank rows/spaces carry geometry.
export function normalizeAAForCopy(value: string): string {
  const lines = value.replaceAll('\r\n', '\n').split('\n');
  while (lines.length > 0 && lines[0].trim().length === 0) lines.shift();
  while (lines.length > 0 && lines.at(-1)?.trim().length === 0) lines.pop();
  const content = lines.filter((line) => line.trim().length > 0);
  const indent = content.length ? Math.min(...content.map((line) => line.match(/^ */)?.[0].length ?? 0)) : 0;
  return lines.map((line) => line.slice(indent).trimEnd()).join('\n');
}

export function prepareAAForCopy(value: string): string {
  return normalizeAAForCopy(value);
}

export function copyHTML(value: string, spec: RenderSpec): string {
  const escaped = value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;').replaceAll(' ', '&nbsp;').replaceAll('\n', '<br>');
  // External editors cannot reliably load a copied web font. Request the same
  // installed typeface, then common monospace fonts; communicate this limit.
  return `<pre style="margin:0;text-align:left;white-space:pre;word-break:normal;overflow-wrap:normal;font-family:'DejaVu Sans Mono',Menlo,Consolas,monospace;font-size:12px;line-height:${spec.cell_height/spec.font_size};letter-spacing:0;font-weight:400;font-variant-ligatures:none">${escaped}</pre>`;
}
