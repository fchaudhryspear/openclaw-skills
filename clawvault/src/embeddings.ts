/**
 * Embedding Utilities
 * Generates vector representations for semantic search
 */

import * as crypto from 'crypto';

// Simple embedding generation using word hashing (for demo purposes)
// In production, use a real embedding model like OpenAI, HuggingFace, etc.
const EMBEDDING_DIMENSION = 128;

export function generateEmbedding(text: string): number[] {
  const normalized = text.toLowerCase().trim();
  const embedding: number[] = new Array(EMBEDDING_DIMENSION).fill(0);
  
  // Generate n-grams and hash them to positions
  const words = tokenize(normalized);
  const ngrams = generateNgrams(words, 1, 3);
  
  for (const ngram of ngrams) {
    const hash = hashString(ngram);
    const position = hash % EMBEDDING_DIMENSION;
    const weight = Math.log(1 + ngram.length) / Math.log(2);
    embedding[position] += weight;
  }
  
  // Normalize to unit vector
  return normalizeVector(embedding);
}

export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error('Vectors must have same dimension');
  }
  
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  
  if (normA === 0 || normB === 0) return 0;
  
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(t => t.length > 1);
}

export function removeStopwords(tokens: string[]): string[] {
  const stopwords = new Set([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
    'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
    'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
    'below', 'between', 'under', 'and', 'but', 'or', 'yet', 'so', 'if',
    'because', 'although', 'though', 'while', 'where', 'when', 'that',
    'which', 'who', 'whom', 'whose', 'what', 'this', 'these', 'those',
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you',
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
    'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them',
    'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this',
    'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did',
    'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as',
    'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against',
    'between', 'into', 'through', 'during', 'before', 'after', 'above',
    'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
    'under', 'again', 'further', 'then', 'once'
  ]);
  
  return tokens.filter(t => !stopwords.has(t));
}

function generateNgrams(words: string[], minN: number, maxN: number): string[] {
  const ngrams: string[] = [];
  
  for (let n = minN; n <= maxN && n <= words.length; n++) {
    for (let i = 0; i <= words.length - n; i++) {
      ngrams.push(words.slice(i, i + n).join('_'));
    }
  }
  
  return ngrams;
}

function hashString(str: string): number {
  return crypto.createHash('md5').update(str).digest().readUInt32LE(0);
}

function normalizeVector(vec: number[]): number[] {
  const norm = Math.sqrt(vec.reduce((sum, val) => sum + val * val, 0));
  if (norm === 0) return vec;
  return vec.map(val => val / norm);
}

export function calculateRecencyBoost(timestamp: number, halfLife: number = 86400000): number {
  const age = Date.now() - timestamp;
  return Math.exp(-age / halfLife);
}

export function extractKeywords(text: string): string[] {
  const tokens = tokenize(text);
  return removeStopwords(tokens);
}
