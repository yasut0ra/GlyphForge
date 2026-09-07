import { copyHTML, type RenderSpec } from './render-contract';

export interface EvaluationRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  issue_type: string;
  description: string;
  priority: number;
}

export interface ScreenshotAssessment {
  subject_score: number;
  silhouette_score: number;
  feature_score: number;
  readability_score: number;
  overall_score: number;
  summary: string;
  suggested_adjustment: string;
  regions: EvaluationRegion[];
}

export interface ScreenshotEvaluationResponse {
  evaluation: ScreenshotAssessment;
  objective_score: number;
  evaluator: string;
}

export interface RefinementResponse {
  optimized_aa: string;
  optimized_preview: string;
  previous_reconstruction_loss: number;
  reconstruction_loss: number;
  ssim: number;
  edge_similarity: number;
  optimization_iterations: number;
  optimization_evaluations: number;
  changed_characters: number;
  grid_width: number;
  grid_height: number;
  render_spec: RenderSpec;
  structure_score: number;
  optimization_passes: number;
  joint_replacements: number;
}

export interface BrowserCapture {
  blob: Blob;
  dataUrl: string;
}

export async function copyAAWithMonospaceFormatting(
  value: string,
  spec: RenderSpec,
): Promise<'rich' | 'plain'> {
  const html = copyHTML(value, spec);
  if (navigator.clipboard.write && typeof ClipboardItem !== 'undefined') {
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/plain': new Blob([value], { type: 'text/plain;charset=utf-8' }),
          'text/html': new Blob([html], { type: 'text/html;charset=utf-8' }),
        }),
      ]);
      return 'rich';
    } catch {
      // Fall back to plain text if rich clipboard writing is unavailable.
    }
  }
  await navigator.clipboard.writeText(value);
  return 'plain';
}

export async function copyPNGToClipboard(blob: Blob): Promise<void> {
  if (!navigator.clipboard.write || typeof ClipboardItem === 'undefined') {
    throw new Error('このブラウザは画像のクリップボードコピーに対応していません。');
  }
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
}

function canvasBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('ブラウザ描画を画像に変換できませんでした。'));
    }, 'image/png');
  });
}

export async function captureBrowserAA(
  aa: string,
  sourceElement: HTMLElement,
  spec: RenderSpec,
): Promise<BrowserCapture> {
  await document.fonts.load(`${spec.font_size}px "${spec.font_family}"`);
  await document.fonts.ready;
  const computed = window.getComputedStyle(sourceElement);
  const fontSize = Number.parseFloat(computed.fontSize) || 12;
  const lineHeight = fontSize * spec.cell_height / spec.font_size;
  const advance = fontSize * spec.cell_width / spec.font_size;
  const font = `${computed.fontWeight} ${fontSize}px ${computed.fontFamily}`;
  const lines = aa.split('\n');
  const cssWidth = Math.max(1, Math.ceil(Math.max(...lines.map((line) => Array.from(line).length)) * advance));
  const cssHeight = Math.max(1, Math.ceil(lines.length * lineHeight));
  const scale = Math.min(2, window.devicePixelRatio || 1);
  const canvas = document.createElement('canvas');
  canvas.width = Math.ceil(cssWidth * scale);
  canvas.height = Math.ceil(cssHeight * scale);
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvasを初期化できませんでした。');
  context.scale(scale, scale);
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, cssWidth, cssHeight);
  context.font = font;
  context.textAlign = 'left';
  context.textBaseline = 'alphabetic';
  context.fontKerning = 'none';
  context.fillStyle = '#111718';
  lines.forEach((line, row) => Array.from(line).forEach((char, col) => {
    context.fillText(char, col * advance, row * lineHeight + fontSize * spec.baseline / spec.font_size);
  }));
  return { blob: await canvasBlob(canvas), dataUrl: canvas.toDataURL('image/png') };
}

export async function dataUrlToBlob(value: string): Promise<Blob> {
  const response = await fetch(value);
  if (!response.ok) throw new Error('参照画像を読み取れませんでした。');
  return response.blob();
}

export async function evaluateScreenshot(
  apiUrl: string,
  plan: object,
  screenshot: Blob,
  reference: Blob,
): Promise<ScreenshotEvaluationResponse> {
  const body = new FormData();
  body.set('plan', JSON.stringify(plan));
  body.set('screenshot', screenshot, 'browser-aa.png');
  body.set('reference', reference, 'reference.png');
  const response = await fetch(`${apiUrl}/api/evaluate-screenshot`, { method: 'POST', body });
  const payload = await response.json() as ScreenshotEvaluationResponse & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? 'スクリーンショット評価に失敗しました。');
  return payload;
}

export async function requestRefinement(
  apiUrl: string,
  input: {
    aa: string;
    width: number;
    style: string;
    detail: string;
    roundNumber: number;
    feedback: ScreenshotAssessment;
    reference: Blob;
    renderProfile: RenderSpec['profile'];
  },
): Promise<RefinementResponse> {
  const body = new FormData();
  body.set('aa', input.aa);
  body.set('width', String(input.width));
  body.set('style', input.style);
  body.set('detail', input.detail);
  body.set('render_profile', input.renderProfile);
  body.set('round_number', String(input.roundNumber));
  body.set('feedback', JSON.stringify(input.feedback));
  body.set('reference', input.reference, 'reference.png');
  const response = await fetch(`${apiUrl}/api/refine`, { method: 'POST', body });
  const payload = await response.json() as RefinementResponse & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? 'フィードバック改善に失敗しました。');
  return payload;
}
