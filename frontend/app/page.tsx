'use client';

import {
  AlertCircle,
  ArrowRight,
  Camera,
  Check,
  CheckCircle2,
  Clipboard,
  ImageIcon,
  ImagePlus,
  Layers3,
  LoaderCircle,
  RefreshCw,
  ScanLine,
  Sparkles,
  X,
} from 'lucide-react';
import Image from 'next/image';
import { SyntheticEvent, useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Progress, ProgressLabel, ProgressValue } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import {
  captureBrowserAA,
  copyAAWithMonospaceFormatting,
  copyPNGToClipboard,
  dataUrlToBlob,
  evaluateScreenshot,
  prepareAAForCopy,
  requestRefinement,
  type CopyProfile,
} from '@/lib/aa-feedback';

type Style = 'pure_ascii' | 'unicode' | 'block';
type Detail = 'simple' | 'normal' | 'detailed';
type OutputView = 'initial' | 'optimized';
type PreviewView = 'reference' | 'rendered';

interface VisualPlan {
  subject: string;
  composition: string;
  view: string;
  important_features: string[];
  style: string;
  width: number;
}

interface Metrics {
  initial_reconstruction_loss: number;
  optimized_reconstruction_loss: number;
  optimization_iterations: number;
  optimization_evaluations: number;
  generation_time_ms: number;
  number_of_characters: number;
  ssim: number;
  edge_similarity: number;
  semantic_score: number;
}

interface GenerationResult {
  plan: VisualPlan;
  initial_aa: string;
  optimized_aa: string;
  reference_image: string;
  initial_preview: string;
  optimized_preview: string;
  metrics: Metrics;
  grid_width: number;
  grid_height: number;
  providers: Record<string, string>;
}

interface FeedbackIteration {
  round: number;
  score: number;
  accepted: boolean;
  changedCharacters: number;
  screenshot: string;
  evaluator: string;
  summary: string;
}

const sampleOptimized = `
           A                A
          / \\              / \\
         /   \\___.--.___/   \\
        /      .-     -.      \\
       |      /  o   o  \\      |
       |     |     ^     |     |
       |      \\  '-'  /      |
        \\      '-._.-'      /
         '._      /|\\      _.'
            '----' | '----'            `;

const sampleInitial = `
           #                A
          @  h            r  h
          /    hMr     s@    [
        @     /  i   i  \\     @
       |     /    o o    \\     |
       |    |      ^      |    |
        \\    irs---sri    /
         'A      / | \\      A'         `;

const defaultResult: GenerationResult = {
  plan: {
    subject: 'cat',
    composition: 'head and shoulders',
    view: 'front',
    important_features: ['triangular ears', 'round eyes', 'whiskers', 'small nose'],
    style: 'crisp monochrome line art optimized for printable ASCII glyphs',
    width: 40,
  },
  initial_aa: sampleInitial,
  optimized_aa: sampleOptimized,
  reference_image: '/sample-reference.png',
  initial_preview: '/sample-aa-initial.png',
  optimized_preview: '/sample-aa-optimized.png',
  metrics: {
    initial_reconstruction_loss: 0.02873,
    optimized_reconstruction_loss: 0.027339,
    optimization_iterations: 54,
    optimization_evaluations: 8850,
    generation_time_ms: 2333,
    number_of_characters: 720,
    ssim: 0.1309,
    edge_similarity: 0.9738,
    semantic_score: 0.82,
  },
  grid_width: 40,
  grid_height: 18,
  providers: {
    planner: 'local heuristic planner',
    image: 'offline procedural line art',
    semantic: 'structural proxy evaluator',
  },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const styleLabels: Record<Style, string> = {
  pure_ascii: 'Pure ASCII',
  unicode: 'Unicode AA',
  block: 'Block Art',
};

function formatLoss(value: number) {
  return value.toFixed(6);
}

function feedbackScore(
  objectiveScore: number,
  reconstructionLoss: number,
  ssim: number,
  edgeSimilarity: number,
) {
  const reconstruction = Math.max(0, 1 - Math.min(1, reconstructionLoss * 4));
  return (
    0.55 * objectiveScore +
    0.2 * edgeSimilarity +
    0.15 * ssim +
    0.1 * reconstruction
  );
}

export default function Home() {
  const [prompt, setPrompt] = useState('猫の顔を横幅40文字で作って');
  const [width, setWidth] = useState(40);
  const [style, setStyle] = useState<Style>('pure_ascii');
  const [detail, setDetail] = useState<Detail>('normal');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GenerationResult>(defaultResult);
  const [outputView, setOutputView] = useState<OutputView>('optimized');
  const [previewView, setPreviewView] = useState<PreviewView>('reference');
  const [copyProfile, setCopyProfile] = useState<CopyProfile>('notes_docs');
  const [loading, setLoading] = useState(false);
  const [improving, setImproving] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState<'aa' | 'png' | null>(null);
  const [hasGenerated, setHasGenerated] = useState(false);
  const [feedbackIterations, setFeedbackIterations] = useState<FeedbackIteration[]>([]);
  const [improvementStatus, setImprovementStatus] = useState('');
  const fileInput = useRef<HTMLInputElement>(null);
  const aaOutput = useRef<HTMLPreElement>(null);

  const sourceAA = outputView === 'optimized' ? result.optimized_aa : result.initial_aa;
  const shownAA = prepareAAForCopy(sourceAA, copyProfile);
  const copyWidth = Math.max(0, ...shownAA.split('\n').map((line) => line.length));
  const copyHeight = shownAA.length > 0 ? shownAA.split('\n').length : 0;
  const shownPreview = previewView === 'reference'
    ? result.reference_image
    : outputView === 'optimized'
      ? result.optimized_preview
      : result.initial_preview;
  const score = Math.round(result.metrics.semantic_score * 100);
  const improvement = result.metrics.initial_reconstruction_loss > 0
    ? ((result.metrics.initial_reconstruction_loss - result.metrics.optimized_reconstruction_loss) /
      result.metrics.initial_reconstruction_loss) * 100
    : 0;

  function chooseFile(next: File | null) {
    if (!next) return;
    if (!next.type.startsWith('image/')) {
      setError('PNG、JPEG、WebPなどの画像ファイルを選択してください。');
      return;
    }
    setError('');
    setFile(next);
  }

  async function generate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim()) {
      setError('生成したい対象を入力してください。');
      return;
    }
    setLoading(true);
    setError('');
    setCopied(null);
    const body = new FormData();
    body.set('prompt', prompt.trim());
    body.set('width', String(width));
    body.set('style', style);
    body.set('detail', detail);
    if (file) body.set('image', file);

    try {
      const response = await fetch(`${API_URL}/api/generate`, { method: 'POST', body });
      const payload = await response.json() as GenerationResult & { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? 'AA生成に失敗しました。');
      setResult(payload as GenerationResult);
      setOutputView('optimized');
      setPreviewView('rendered');
      setHasGenerated(true);
      setFeedbackIterations([]);
      setImprovementStatus('');
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'バックエンドに接続できませんでした。';
      setError(`${message} FastAPI が localhost:8000 で起動しているか確認してください。`);
    } finally {
      setLoading(false);
    }
  }

  async function copyAA() {
    try {
      await copyAAWithMonospaceFormatting(shownAA, copyProfile);
      setCopied('aa');
      window.setTimeout(() => setCopied(null), 1800);
    } catch {
      setError('AAをクリップボードへコピーできませんでした。');
    }
  }

  async function copyPNG() {
    if (!aaOutput.current) return;
    try {
      const capture = await captureBrowserAA(shownAA, aaOutput.current);
      await copyPNGToClipboard(capture.blob);
      setCopied('png');
      window.setTimeout(() => setCopied(null), 1800);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : '画像をコピーできませんでした。';
      setError(message);
    }
  }

  async function improveWithScreenshot() {
    if (!aaOutput.current || !hasGenerated) return;
    setImproving(true);
    setError('');
    setCopied(null);
    setOutputView('optimized');
    setPreviewView('rendered');
    setFeedbackIterations([]);

    try {
      const reference = await dataUrlToBlob(result.reference_image);
      let best = result;
      let capture = await captureBrowserAA(
        prepareAAForCopy(best.optimized_aa, copyProfile),
        aaOutput.current,
      );
      let evaluated = await evaluateScreenshot(API_URL, best.plan, capture.blob, reference);
      let bestFeedback = evaluated.evaluation;
      let bestScore = feedbackScore(
        evaluated.objective_score,
        best.metrics.optimized_reconstruction_loss,
        best.metrics.ssim,
        best.metrics.edge_similarity,
      );
      const history: FeedbackIteration[] = [{
        round: 0,
        score: bestScore,
        accepted: true,
        changedCharacters: 0,
        screenshot: capture.dataUrl,
        evaluator: evaluated.evaluator,
        summary: bestFeedback.summary,
      }];
      setFeedbackIterations([...history]);

      for (let round = 1; round <= 2; round += 1) {
        setImprovementStatus(`スクリーンショット評価から改善中 ${round}/2`);
        const candidate = await requestRefinement(API_URL, {
          aa: best.optimized_aa,
          width: best.grid_width,
          style,
          detail,
          roundNumber: round,
          feedback: bestFeedback,
          reference,
        });
        capture = await captureBrowserAA(
          prepareAAForCopy(candidate.optimized_aa, copyProfile),
          aaOutput.current,
        );
        evaluated = await evaluateScreenshot(API_URL, best.plan, capture.blob, reference);
        const candidateScore = feedbackScore(
          evaluated.objective_score,
          candidate.reconstruction_loss,
          candidate.ssim,
          candidate.edge_similarity,
        );
        // The backend only returns globally improving moves, but losses are rounded to 6 decimals.
        const reconstructionImproved =
          candidate.reconstruction_loss <= candidate.previous_reconstruction_loss + 1e-6;
        const browserScoreStable = candidateScore + 0.03 >= bestScore;
        const accepted =
          candidate.changed_characters > 0 && reconstructionImproved && browserScoreStable;
        history.push({
          round,
          score: candidateScore,
          accepted,
          changedCharacters: candidate.changed_characters,
          screenshot: capture.dataUrl,
          evaluator: evaluated.evaluator,
          summary: evaluated.evaluation.summary,
        });
        setFeedbackIterations([...history]);

        if (accepted) {
          bestScore = candidateScore;
          bestFeedback = evaluated.evaluation;
          best = {
            ...best,
            optimized_aa: candidate.optimized_aa,
            optimized_preview: candidate.optimized_preview,
            grid_height: candidate.grid_height,
            providers: { ...best.providers, semantic: evaluated.evaluator },
            metrics: {
              ...best.metrics,
              optimized_reconstruction_loss: candidate.reconstruction_loss,
              optimization_iterations:
                best.metrics.optimization_iterations + candidate.optimization_iterations,
              optimization_evaluations:
                best.metrics.optimization_evaluations + candidate.optimization_evaluations,
              ssim: candidate.ssim,
              edge_similarity: candidate.edge_similarity,
              semantic_score: evaluated.evaluation.overall_score,
            },
          };
          setResult(best);
        }
        if (candidate.changed_characters === 0) break;
      }
      const acceptedCount = history.filter((entry) => entry.round > 0 && entry.accepted).length;
      setImprovementStatus(
        acceptedCount > 0
          ? `${acceptedCount}回の改善を採用しました`
          : '最高スコアを維持しました（悪化候補は不採用）',
      );
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'スクリーンショット改善に失敗しました。';
      setError(message);
      setImprovementStatus('');
    } finally {
      setImproving(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="flex h-16 items-center justify-between border-b bg-background/95 px-5 backdrop-blur md:px-8">
        <div className="flex items-center gap-3">
          <div className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground shadow-[3px_3px_0_var(--ink)]">
            <ScanLine className="size-4" strokeWidth={2.4} />
          </div>
          <div>
            <p className="font-semibold leading-none tracking-[-0.02em]">GlyphForge</p>
            <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">Shape-aware AA lab</p>
          </div>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <Badge variant="outline" className="rounded-md font-mono text-[10px] uppercase tracking-wider">
            <span className="size-1.5 rounded-full bg-emerald-500" /> Local engine
          </Badge>
          <span className="text-xs text-muted-foreground">v0.1 MVP</span>
        </div>
      </header>

      <section className="lab-grid min-h-[calc(100vh-4rem)]">
        <aside className="border-b bg-card p-5 lg:border-b-0 lg:border-r lg:p-6">
          <div className="mb-6 flex items-start gap-3">
            <span className="step-chip">01</span>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">何を描きますか？</h1>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">言葉から輪郭を計画し、文字の形で再構築します。</p>
            </div>
          </div>

          <form className="space-y-5" onSubmit={generate}>
            <label className="control-group" htmlFor="prompt">
              <span className="control-label">プロンプト</span>
              <Textarea
                id="prompt"
                className="min-h-28 resize-none bg-background leading-relaxed"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="例：宇宙船をレトロなASCII Artで"
              />
              <span className="text-[11px] text-muted-foreground">対象・構図・雰囲気を自然な言葉で入力</span>
            </label>

            <div className="control-group">
              <span className="control-label">横幅</span>
              <div className="flex items-center gap-3">
                <Input
                  aria-label="AAの横幅"
                  type="range"
                  min="20"
                  max="120"
                  step="1"
                  value={width}
                  onChange={(event) => setWidth(Number(event.target.value))}
                  className="h-2 flex-1 cursor-pointer appearance-none border-0 bg-muted p-0 accent-primary"
                />
                <div className="relative w-20">
                  <Input
                    aria-label="AAの横幅（数値）"
                    type="number"
                    min="20"
                    max="120"
                    value={width}
                    onChange={(event) => setWidth(Math.min(120, Math.max(20, Number(event.target.value))))}
                    className="h-9 bg-background pr-8 font-mono font-semibold"
                  />
                  <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 font-mono text-[9px] text-muted-foreground">ch</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="control-group" htmlFor="style">
                <span className="control-label">AA スタイル</span>
                <NativeSelect id="style" value={style} onChange={(event) => setStyle(event.target.value as Style)} className="w-full">
                  <NativeSelectOption value="pure_ascii">Pure ASCII</NativeSelectOption>
                  <NativeSelectOption value="unicode">Unicode AA</NativeSelectOption>
                  <NativeSelectOption value="block">Block Art</NativeSelectOption>
                </NativeSelect>
              </label>
              <label className="control-group" htmlFor="detail">
                <span className="control-label">詳細度</span>
                <NativeSelect id="detail" value={detail} onChange={(event) => setDetail(event.target.value as Detail)} className="w-full">
                  <NativeSelectOption value="simple">Simple</NativeSelectOption>
                  <NativeSelectOption value="normal">Normal</NativeSelectOption>
                  <NativeSelectOption value="detailed">Detailed</NativeSelectOption>
                </NativeSelect>
              </label>
            </div>

            <input
              ref={fileInput}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
            />
            <button
              className="upload-zone"
              type="button"
              onClick={() => fileInput.current?.click()}
            >
              {file ? <CheckCircle2 className="size-5 text-secondary" /> : <ImagePlus className="size-5 text-primary" />}
              <span className="min-w-0 flex-1">
                <strong className="truncate">{file ? file.name : '参照画像を追加'}</strong>
                <small>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB · 変換に使用` : 'PNG / JPG / WebP · 任意'}</small>
              </span>
              {file && <X className="size-4 text-muted-foreground" aria-hidden="true" />}
            </button>

            {error && (
              <p role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs leading-relaxed text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" /> {error}
              </p>
            )}

            <Button type="submit" size="lg" disabled={loading} className="h-11 w-full justify-between px-4 shadow-[3px_3px_0_var(--ink)]">
              <span className="flex items-center gap-2">
                {loading ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                {loading ? '輪郭を最適化中…' : 'AAを生成'}
              </span>
              <ArrowRight className="size-4" />
            </Button>
            <p className="text-center text-[10px] leading-relaxed text-muted-foreground">画像なしの場合はAPI設定に応じて参照線画を生成。<br />APIキーなしでもオフラインデモが動作します。</p>
          </form>
        </aside>

        <section className="min-w-0 bg-[#ebe6dc] p-4 sm:p-6 lg:p-8">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="step-chip">02</span>
              <div>
                <h2 className="font-semibold tracking-tight">Generated output</h2>
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{copyWidth} × {copyHeight} copy · {result.grid_width} × {result.grid_height} grid · {styleLabels[style]}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <NativeSelect
                aria-label="貼り付け先プロファイル"
                value={copyProfile}
                onChange={(event) => setCopyProfile(event.target.value as CopyProfile)}
                className="h-8 w-36 bg-background text-[10px]"
              >
                <NativeSelectOption value="notes_docs">Notes / Docs</NativeSelectOption>
                <NativeSelectOption value="monospace">Code / Terminal</NativeSelectOption>
              </NativeSelect>
              <div className="segment-control" aria-label="出力比較">
                <button type="button" data-active={outputView === 'initial'} onClick={() => setOutputView('initial')}>Initial</button>
                <button type="button" data-active={outputView === 'optimized'} onClick={() => setOutputView('optimized')}>Optimized</button>
              </div>
              <Button variant="outline" size="sm" className="bg-background" onClick={copyAA} title="等幅書式付きテキストとしてコピー">
                {copied === 'aa' ? <Check /> : <Clipboard />} {copied === 'aa' ? 'Copied' : 'Copy AA'}
              </Button>
              <Button variant="outline" size="sm" className="bg-background" onClick={copyPNG} title="表示を崩さないPNG画像としてコピー">
                {copied === 'png' ? <Check /> : <ImageIcon />} {copied === 'png' ? 'Copied' : 'Copy PNG'}
              </Button>
            </div>
          </div>

          <div className="aa-stage relative" aria-busy={loading}>
            <div className="stage-toolbar">
              <div className="flex gap-1.5"><span className="traffic bg-[#ed6b5f]" /><span className="traffic bg-[#f4bf4f]" /><span className="traffic bg-[#61c554]" /></div>
              <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/45">{outputView}.txt</span>
              <span className="rounded bg-white/10 px-2 py-1 font-mono text-[9px] text-white/55">100%</span>
            </div>
            <div className="aa-viewport">
              <pre
                ref={aaOutput}
                className="aa-output"
                data-copy-profile={copyProfile}
                aria-label={`生成された${result.plan.subject}のAA`}
                style={{ fontSize: result.grid_width > 90 ? '6px' : result.grid_width > 60 ? '8px' : undefined }}
              >{shownAA}</pre>
            </div>
            <div className="stage-footer">
              <span className="flex items-center gap-1.5"><Check className="size-3.5 text-[#75d8c7]" /> {outputView === 'optimized' ? 'Optimization complete' : 'Initial reconstruction'}</span>
              <span>copy-ready · common margin removed</span>
            </div>
            {(loading || improving) && (
              <div className="absolute inset-0 grid place-items-center bg-[#111718]/85 backdrop-blur-[2px]">
                <div className="text-center text-white">
                  <LoaderCircle className="mx-auto size-7 animate-spin text-[#75d8c7]" />
                  <p className="mt-3 text-sm font-medium">{improving ? 'Browser feedbackを反映中' : 'Glyph candidatesを探索中'}</p>
                  <p className="mt-1 font-mono text-[10px] text-white/45">{improving ? improvementStatus : 'pixel + edge + orientation loss'}</p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 flex items-center gap-3 rounded-lg border border-black/10 bg-white/50 px-4 py-3 text-xs text-muted-foreground">
            <Layers3 className="size-4 shrink-0 text-secondary" />
            glyph画像の画素・エッジ方向・密度を照合し、3×3近傍で局所探索しました。
          </div>
        </section>

        <aside className="border-t bg-card p-5 lg:border-l lg:border-t-0 lg:p-6">
          <div className="mb-5 flex items-start gap-3">
            <span className="step-chip">03</span>
            <div className="flex-1">
              <h2 className="font-semibold tracking-tight">Inspect</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">参照画像と再構成品質</p>
            </div>
          </div>

          <div className="space-y-5">
            <figure>
              <div className="mb-2 flex items-center justify-between gap-2">
                <figcaption className="control-label">Visual preview</figcaption>
                <div className="segment-control compact" aria-label="画像プレビュー切替">
                  <button type="button" data-active={previewView === 'reference'} onClick={() => setPreviewView('reference')}><ImageIcon /> Ref</button>
                  <button type="button" data-active={previewView === 'rendered'} onClick={() => setPreviewView('rendered')}><ScanLine /> AA</button>
                </div>
              </div>
              <div className="checkerboard overflow-hidden rounded-lg border">
                <Image
                  unoptimized
                  src={shownPreview}
                  width={640}
                  height={480}
                  alt={previewView === 'reference' ? '変換に使った参照画像' : 'AAを固定幅フォントで再描画した画像'}
                  className="aspect-[4/3] h-full w-full object-contain mix-blend-multiply"
                />
              </div>
              <p className="mt-2 truncate font-mono text-[9px] text-muted-foreground">{previewView === 'reference' ? result.providers.image : `${outputView} monospace rendering`}</p>
            </figure>

            <div className="metric-block">
              <div className="flex items-end justify-between">
                <div><span className="control-label">Generation score</span><p className="mt-1 text-3xl font-semibold tracking-[-0.05em]">{score}<span className="text-base text-muted-foreground">/100</span></p></div>
                <Badge className="rounded-md bg-secondary text-secondary-foreground">{improvement >= 0 ? '+' : ''}{improvement.toFixed(1)}%</Badge>
              </div>
              <Progress value={score} className="mt-4">
                <ProgressLabel className="sr-only">Generation score</ProgressLabel>
                <ProgressValue className="sr-only" />
              </Progress>
            </div>

            <dl className="divide-y border-y text-xs">
              <div className="metric-row"><dt>Initial loss</dt><dd>{formatLoss(result.metrics.initial_reconstruction_loss)}</dd></div>
              <div className="metric-row"><dt>Optimized loss</dt><dd className="text-secondary">{formatLoss(result.metrics.optimized_reconstruction_loss)}</dd></div>
              <div className="metric-row"><dt>Edge similarity</dt><dd>{(result.metrics.edge_similarity * 100).toFixed(2)}%</dd></div>
              <div className="metric-row"><dt>SSIM</dt><dd>{result.metrics.ssim.toFixed(4)}</dd></div>
              <div className="metric-row"><dt>Iterations</dt><dd>{result.metrics.optimization_iterations} / {result.metrics.optimization_evaluations.toLocaleString()}</dd></div>
              <div className="metric-row"><dt>Generation time</dt><dd>{(result.metrics.generation_time_ms / 1000).toFixed(2)} sec</dd></div>
            </dl>

            <div className="rounded-lg border bg-background p-3">
              <p className="control-label mb-2">Visual plan</p>
              <p className="text-sm font-medium capitalize">{result.plan.subject} · {result.plan.composition}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">{result.plan.view} · {result.plan.style}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {result.plan.important_features.map((feature) => <Badge key={feature} variant="outline" className="rounded font-mono text-[9px]">{feature}</Badge>)}
              </div>
            </div>

            <div className="rounded-lg border bg-background p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="control-label">Visual feedback loop</p>
                  <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">実ブラウザ描画を評価し、最大2回だけ再探索します。</p>
                </div>
                <Camera className="size-4 shrink-0 text-secondary" />
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="mt-3 w-full"
                disabled={!hasGenerated || loading || improving}
                onClick={improveWithScreenshot}
              >
                {improving ? <LoaderCircle className="animate-spin" /> : <RefreshCw />}
                {improving ? '評価・改善中…' : 'Screenshotで2回改善'}
              </Button>
              {!hasGenerated && <p className="mt-2 text-center text-[9px] text-muted-foreground">まずAAを生成してください</p>}
              {improvementStatus && !improving && <p className="mt-2 text-[10px] font-medium text-secondary">{improvementStatus}</p>}
              {feedbackIterations.length > 0 && (
                <div className="mt-3 space-y-2 border-t pt-3">
                  {feedbackIterations.map((entry) => (
                    <div key={entry.round} className="flex items-center gap-2 text-[10px]">
                      <span className="grid size-5 place-items-center rounded bg-muted font-mono">{entry.round}</span>
                      <span className="flex-1 truncate">{entry.round === 0 ? 'Baseline' : `${entry.changedCharacters} glyph changes`}</span>
                      <span className="font-mono font-semibold">{(entry.score * 100).toFixed(1)}</span>
                      <Badge variant={entry.accepted ? 'default' : 'outline'} className="rounded px-1.5 py-0 text-[8px]">
                        {entry.accepted ? 'KEEP' : 'DROP'}
                      </Badge>
                    </div>
                  ))}
                  <p className="line-clamp-2 text-[9px] leading-relaxed text-muted-foreground">{feedbackIterations.at(-1)?.summary}</p>
                </div>
              )}
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
