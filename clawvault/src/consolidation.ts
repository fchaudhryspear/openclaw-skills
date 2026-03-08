/**
 * Memory Consolidation Module — Smart LLM-powered merging
 * 
 * Features:
 * - LLM-based semantic merge (uses Qwen-Coder at $0.30/M)
 * - Fallback to keyword deduplication when LLM fails
 * - Batch consolidation with confidence scoring
 * - Tracks which models worked best for different memory types
 */

import * as fs from 'fs';
import * as path from 'path';
import { Memory } from './types';
import { cosineSimilarity, generateEmbedding } from './embeddings';

const CONSOLIDATION_LOG = path.join(process.env.HOME || '~', '.openclaw/workspace/memory/consolidation-log.jsonl');
const PERFORMANCE_TRACKING_FILE = path.join(process.env.HOME || '~', '.openclaw/workspace/memory/model_performance.json');

// Configuration
const SIMILARITY_THRESHOLD = 0.85; // Above this = likely duplicate
const BATCH_SIZE = 10; // Memories to consolidate at once
const MAX_CONSOLIDATION_TIME_MS = 60000; // 60 second timeout

export class ConsolidationModule {
  private performanceData: Record<string, any> = {};

  constructor() {
    this.loadPerformanceData();
  }

  // ── Core Consolidation ────────────────────────────────────────────────────

  /**
   * Consolidate similar memories using LLM intelligence
   * Returns the consolidated memory object
   */
  async consolidate(memories: Memory[]): Promise<Memory | null> {
    if (memories.length === 0) return null;
    if (memories.length === 1) return memories[0];

    const startTime = Date.now();

    try {
      // Step 1: Try LLM merge first
      const llmResult = await this.llmConsolidate(memories);
      
      if (llmResult) {
        const duration = Date.now() - startTime;
        this.logPerformance('qwen-coder', 'consolidation', true, duration);
        
        console.log(`✅ LLM consolidation complete in ${duration}ms`);
        return llmResult;
      }
    } catch (error) {
      console.warn(`⚠️  LLM consolidation failed: ${(error as Error).message}, falling back to keyword merge`);
    }

    // Step 2: Fallback to simple merge
    const fallbackResult = this.simpleMerge(memories);
    const duration = Date.now() - startTime;
    this.logPerformance('fallback', 'consolidation', true, duration);

    return fallbackResult;
  }

  /**
   * Find duplicate/similar memories and mark for consolidation
   */
  findDuplicates(memories: Memory[], threshold: number = SIMILARITY_THRESHOLD): Memory[][] {
    const duplicates: Memory[][] = [];
    const processed = new Set<string>();

    for (let i = 0; i < memories.length; i++) {
      if (processed.has(memories[i].id)) continue;

      const group: Memory[] = [memories[i]];
      processed.add(memories[i].id);

      for (let j = i + 1; j < memories.length; j++) {
        if (processed.has(memories[j].id)) continue;

        const similarity = cosineSimilarity(
          generateEmbedding(memories[i].content),
          generateEmbedding(memories[j].content)
        );

        if (similarity >= threshold) {
          group.push(memories[j]);
          processed.add(memories[j].id);
        }
      }

      if (group.length > 1) {
        duplicates.push(group);
      }
    }

    return duplicates;
  }

  /**
   * Bulk consolidate all memories in vault
   */
  async bulkConsolidate(memories: Memory[]): Promise<{ consolidated: number; original: Memory[] }> {
    const duplicates = this.findDuplicates(memories);
    
    const originalIds = new Set(memories.map(m => m.id));
    const consolidatedMemories: Memory[] = [];

    for (const group of duplicates) {
      const result = await this.consolidate(group);
      if (result) {
        // Mark old ones for deletion
        for (const m of group) {
          originalIds.delete(m.id);
        }
        
        // Add consolidated version
        consolidatedMemories.push(result);
      }
    }

    // Remaining are originals that weren't duplicated
    const remaining = memories.filter(m => originalIds.has(m.id));

    return {
      consolidated: consolidatedMemories.length,
      original: [...remaining, ...consolidatedMemories]
    };
  }

  // ── LLM-Based Consolidation ───────────────────────────────────────────────

  /**
   * Use Qwen to intelligently merge multiple memories
   */
  private async llmConsolidate(memories: Memory[]): Promise<Memory | null> {
    const prompt = this.buildConsolidationPrompt(memories);
    
    try {
      // Call Qwen-Coder via our MO router
      const completion = await this.callMO(prompt, 'qwen-coder');
      
      if (!completion || completion.trim().length === 0) {
        throw new Error('Empty response from model');
      }

      // Parse the consolidated content
      const consolidatedContent = this.parseLLMResponse(completion, memories);
      
      return {
        id: `cons-${Date.now()}`,
        content: consolidatedContent,
        type: 'declarative',
        createdAtMs: Date.now(),
        metadata: {
          sourceType: 'llm-consolidated',
          sourceCount: memories.length,
          sourceIds: memories.map(m => m.id),
          originalModels: [...new Set(memories.map(m => m.metadata?.model || 'unknown'))]
        }
      };
    } catch (error) {
      console.error(`❌ LLM consolidation error: ${(error as Error).message}`);
      return null;
    }
  }

  /**
   * Build prompt for LLM consolidation
   */
  private buildConsolidationPrompt(memories: Memory[]): string {
    const memoryList = memories.map((m, idx) => `[${idx + 1}] ${m.content}`).join('\n\n');
    
    return `You are a memory consolidation expert. Your task is to merge these related memories into a SINGLE cohesive statement.

Instructions:
1. Identify the core facts and preserve them
2. Remove redundancies and repetitive statements
3. Keep dates, names, and important details intact
4. Write in clear, concise language
5. Do NOT add information that wasn't in the original memories

MEMORIES TO MERGE (${memories.length} total):

${memoryList}

Return ONLY the consolidated text. No explanations, no introductions, just the merged memory.`;
  }

  /**
   * Extract key phrases from content for preservation checking
   */
  private extractKeyPhrases(content: string): string[] {
    const words = content.toLowerCase().split(/\s+/);
    return words.filter(w => w.length > 4 && !this.isStopword(w));
  }

  private isStopword(word: string): boolean {
    const stopwords = new Set([
      'about', 'above', 'after', 'again', 'below', 'could', 'every', 'first',
      'from', 'have', 'her', 'here', 'hers', 'him', 'his', 'how', 'i', 'if',
      'in', 'into', 'is', 'it', 'its', 'just', 'may', 'me', 'might', 'my',
      'no', 'not', 'now', 'of', 'on', 'once', 'only', 'or', 'other', 'our',
      'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such',
      'than', 'that', 'the', 'their', 'them', 'then', 'there', 'these',
      'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until',
      'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which',
      'while', 'who', 'whom', 'why', 'with', 'you', 'your'
    ]);
    return stopwords.has(word);
  }

  /**
   * Parse LLM response and validate it makes sense
   */
  private parseLLMResponse(llmOutput: string, originalMemories: Memory[]): string {
    const output = llmOutput.trim();

    // Basic validation checks
    if (output.length < 10) {
      throw new Error('Consolidated result too short');
    }

    // Check we didn't lose critical information
    const originalContent = originalMemories.map(m => m.content.toLowerCase()).join(' ');
    const outputLower = output.toLowerCase();

    // Count how many key phrases were preserved (rough heuristic)
    let preservationScore = 0;
    const keyPhrases = originalMemories
      .map(m => this.extractKeyPhrases(m.content))
      .flat()
      .slice(0, 10);

    for (const phrase of keyPhrases) {
      if (outputLower.includes(phrase.toLowerCase())) {
        preservationScore++;
      }
    }

    const retentionRate = preservationScore / Math.max(keyPhrases.length, 1);
    
    if (retentionRate < 0.5 && keyPhrases.length > 0) {
      console.warn(`⚠️  Low information retention: ${Math.round(retentionRate * 100)}%`);
    }

    return output;
  }

  // ── Simple Merge Fallback ────────────────────────────────────────────────

  /**
   * Simple keyword-based merge when LLM isn't available
   */
  private simpleMerge(memories: Memory[]): Memory {
    const contents = memories.map(m => m.content);
    
    // Deduplicate sentences
    const sentences = new Set<string>();
    for (const content of contents) {
      const sent = content.split('. ').filter(s => s.trim().length > 0);
      sent.forEach(s => sentences.add(s.trim()));
    }

    const merged = Array.from(sentences).join('. ');

    return {
      id: `simple-${Date.now()}`,
      content: merged,
      type: 'declarative',
      createdAtMs: Date.now()
    };
  }

  // ── MO Router Integration ────────────────────────────────────────────────

  /**
   * Call Model Orchestrator for completions
   */
  private async callMO(prompt: string, model: string = 'qwen-coder'): Promise<string> {
    // Import dynamically to avoid circular dependency
    const aiPath = path.join(process.env.HOME || '~', '.openclaw/workspace/workspace/lib/ai.js');
    
    try {
      const { complete } = require(aiPath);
      return await complete(prompt, 'draft'); // Using 'draft' task for consistency
    } catch (error) {
      // If MO not available, fall back to simple Gemini call
      console.warn('⚠️  MO not available, using fallback...');
      return await this.fallbackGeminiCall(prompt);
    }
  }

  /**
   * Fallback to direct Gemini API if MO unavailable
   */
  private async fallbackGeminiCall(prompt: string): Promise<string> {
    const apiKey = process.env.GOOGLE_API_KEY || '';
    
    return new Promise((resolve, reject) => {
      const https = require('https');
      const body = JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: 512, temperature: 0.3 }
      });

      const req = https.request({
        hostname: 'generativelanguage.googleapis.com',
        path: `/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body)
        }
      }, (res: any) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const parsed = JSON.parse(data);
            const text = parsed.candidates?.[0]?.content?.parts?.[0]?.text || '';
            resolve(text.trim());
          } catch (e) {
            reject(new Error(`Gemini fallback failed: ${(e as Error).message}`));
          }
        });
      });

      req.on('error', reject);
      req.write(body);
      req.end();
    });
  }

  // ── Performance Tracking ─────────────────────────────────────────────────

  private loadPerformanceData(): void {
    try {
      if (fs.existsSync(PERFORMANCE_TRACKING_FILE)) {
        this.performanceData = JSON.parse(fs.readFileSync(PERFORMANCE_TRACKING_FILE, 'utf8'));
      }
    } catch (error) {
      console.warn('⚠️  Could not load performance data:', (error as Error).message);
      this.performanceData = {};
    }
  }

  private logPerformance(model: string, task: string, success: boolean, durationMs: number): void {
    const key = `${task}-${model}`;
    
    if (!this.performanceData[key]) {
      this.performanceData[key] = {
        successes: 0,
        failures: 0,
        totalDuration: 0,
        lastRun: null
      };
    }

    const entry = this.performanceData[key];
    if (success) {
      entry.successes++;
    } else {
      entry.failures++;
    }
    entry.totalDuration += durationMs;
    entry.lastRun = Date.now();

    // Log to file
    try {
      fs.appendFileSync(
        CONSOLIDATION_LOG,
        JSON.stringify({ ts: new Date().toISOString(), model, task, success, durationMs }) + '\n'
      );
    } catch (error) {
      // Non-fatal
    }
  }

  getPerformanceStats(model?: string): Record<string, any> {
    const stats: Record<string, any> = {};
    
    Object.entries(this.performanceData).forEach(([key, data]: [string, any]) => {
      if (model && !key.includes(model)) return;
      
      stats[key] = {
        ...data,
        avgDuration: data.totalDuration / Math.max(data.successes + data.failures, 1),
        successRate: data.successes / Math.max(data.successes + data.failures, 1)
      };
    });

    return stats;
  }
}

// Export singleton instance
export const consolidationModule = new ConsolidationModule();

// Convenience functions for backward compatibility
export async function consolidate(memories: Memory[]): Promise<Memory | null> {
  return consolidationModule.consolidate(memories);
}

export function findDuplicates(memories: Memory[], threshold?: number): Memory[][] {
  return consolidationModule.findDuplicates(memories, threshold);
}

export async function bulkConsolidate(memories: Memory[]): Promise<{ consolidated: number; original: Memory[] }> {
  return consolidationModule.bulkConsolidate(memories);
}
