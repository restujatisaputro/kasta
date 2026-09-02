/**
 * Client-side text recognition for receipt photos.
 *
 * The backend never looks at pixels itself — `POST /receipt-scans` expects a
 * `raw_ocr` text blob (see apps/api .../ocr/service.py) that its Indonesian
 * receipt parser then turns into structured fields (merchant, total, date, …).
 * On Android that text comes from on-device Google ML Kit; in the browser we
 * get there with Tesseract.js (WASM, runs fully client-side).
 */
import type { Worker } from 'tesseract.js';

export interface RecognizeProgress {
  status: string;
  progress: number;
}

let workerPromise: Promise<Worker> | null = null;
let currentProgressListener: ((update: RecognizeProgress) => void) | undefined;

async function getWorker(): Promise<Worker> {
  if (!workerPromise) {
    const { createWorker } = await import('tesseract.js');
    workerPromise = createWorker('ind+eng', undefined, {
      logger: (message) => currentProgressListener?.({ status: message.status, progress: message.progress }),
    }).catch((error: unknown) => {
      workerPromise = null;
      throw error;
    });
  }
  return workerPromise;
}

/** Recognises the text on a receipt photo. Resolves to "" if nothing legible is found. */
export async function recognizeReceiptText(
  file: File | Blob,
  onProgress?: (update: RecognizeProgress) => void,
): Promise<string> {
  const worker = await getWorker();
  currentProgressListener = onProgress;
  try {
    const {
      data: { text },
    } = await worker.recognize(file);
    return text ?? '';
  } finally {
    currentProgressListener = undefined;
  }
}

/** Releases the Tesseract worker (and its WASM memory). Safe to call even if never started. */
export async function terminateReceiptOcr(): Promise<void> {
  if (!workerPromise) return;
  const pending = workerPromise;
  workerPromise = null;
  const worker = await pending.catch(() => null);
  await worker?.terminate();
}
