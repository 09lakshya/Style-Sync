import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a backend 0–1 score (classification confidence, CLIP similarity) as a
 * percentage string. Returns null when the score is absent or not a number so
 * callers can render their own "not available" state. 0 is a valid score.
 */
export function formatScore(value?: number | null, fractionDigits = 0): string | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null
  return `${(value * 100).toFixed(fractionDigits)}%`
}
