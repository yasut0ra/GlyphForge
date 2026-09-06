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
}

export interface BrowserCapture {
  blob: Blob;
  dataUrl: string;
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
): Promise<BrowserCapture> {
  await document.fonts.ready;
  const computed = window.getComputedStyle(sourceElement);
  const fontSize = Number.parseFloat(computed.fontSize) || 12;
  const parsedLineHeight = Number.parseFloat(computed.lineHeight);
  const lineHeight = Number.isFinite(parsedLineHeight) ? parsedLineHeight : fontSize * 1.18;
  const font = `${computed.fontWeight} ${fontSize}px ${computed.fontFamily}`;
  const lines = aa.split('\n');
  const measuring = document.createElement('canvas').getContext('2d');
  if (!measuring) throw new Error('Canvasを初期化できませんでした。');
  measuring.font = font;
  const textWidth = Math.max(1, ...lines.map((line) => measuring.measureText(line || ' ').width));
  const padding = Math.max(16, Math.ceil(fontSize * 1.5));
  const cssWidth = Math.ceil(textWidth + padding * 2);
  const cssHeight = Math.ceil(lines.length * lineHeight + padding * 2);
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
  context.textBaseline = 'top';
  context.fillStyle = '#111718';
  lines.forEach((line, index) => context.fillText(line, padding, padding + index * lineHeight));
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
  },
): Promise<RefinementResponse> {
  const body = new FormData();
  body.set('aa', input.aa);
  body.set('width', String(input.width));
  body.set('style', input.style);
  body.set('detail', input.detail);
  body.set('round_number', String(input.roundNumber));
  body.set('feedback', JSON.stringify(input.feedback));
  body.set('reference', input.reference, 'reference.png');
  const response = await fetch(`${apiUrl}/api/refine`, { method: 'POST', body });
  const payload = await response.json() as RefinementResponse & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? 'フィードバック改善に失敗しました。');
  return payload;
}
