"use strict";
/**
 * Phase 1: Semantic Layer
 * Extracts semantic meaning from memory content
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SemanticLayerBuilder = void 0;
const embeddings_1 = require("./embeddings");
class SemanticLayerBuilder {
    constructor() {
        this.categories = new Map([
            ['technical', ['code', 'api', 'database', 'server', 'function', 'class', 'bug', 'error', 'debug', 'deploy']],
            ['personal', ['name', 'birthday', 'family', 'friend', 'hobby', 'like', 'dislike', 'preference']],
            ['task', ['todo', 'task', 'deadline', 'schedule', 'meeting', 'reminder', 'commitment', 'goal']],
            ['knowledge', ['fact', 'learn', 'study', 'research', 'concept', 'theory', 'principle']],
            ['communication', ['email', 'message', 'call', 'chat', 'conversation', 'discuss', 'talk']],
            ['location', ['address', 'place', 'city', 'country', 'travel', 'visit', 'location']],
            ['financial', ['money', 'price', 'cost', 'budget', 'payment', 'purchase', 'expense']]
        ]);
    }
    build(content) {
        const tokens = (0, embeddings_1.removeStopwords)((0, embeddings_1.tokenize)(content));
        const entities = this.extractEntities(content);
        const concepts = this.extractConcepts(tokens);
        const category = this.determineCategory(tokens);
        const sentiment = this.analyzeSentiment(content);
        const importance = this.assessImportance(content, entities, concepts);
        return {
            category,
            entities,
            concepts,
            sentiment: Math.round(sentiment * 100) / 100,
            importance: Math.round(importance * 100) / 100
        };
    }
    extractEntities(content) {
        const entities = [];
        // Capitalized words (proper nouns)
        const properNouns = content.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g) || [];
        entities.push(...properNouns.filter(e => e.length > 2));
        // Quoted text
        const quoted = content.match(/"([^"]+)"/g) || [];
        entities.push(...quoted.map(q => q.slice(1, -1)));
        // Dates
        const dates = content.match(/\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s+\d{4})?)\b/gi) || [];
        entities.push(...dates);
        // URLs
        const urls = content.match(/https?:\/\/[^\s]+/g) || [];
        entities.push(...urls);
        return [...new Set(entities)].slice(0, 10);
    }
    extractConcepts(tokens) {
        // Extract n-grams that appear meaningful
        const concepts = [];
        // Bigrams and trigrams
        for (let i = 0; i < tokens.length - 1; i++) {
            concepts.push(`${tokens[i]} ${tokens[i + 1]}`);
            if (i < tokens.length - 2) {
                concepts.push(`${tokens[i]} ${tokens[i + 1]} ${tokens[i + 2]}`);
            }
        }
        // Filter to unique concepts and limit
        return [...new Set(concepts)].slice(0, 15);
    }
    determineCategory(tokens) {
        const tokenSet = new Set(tokens);
        let bestCategory = 'general';
        let maxScore = 0;
        for (const [category, keywords] of this.categories) {
            const score = keywords.filter(k => tokenSet.has(k) || tokens.some(t => t.includes(k))).length;
            if (score > maxScore) {
                maxScore = score;
                bestCategory = category;
            }
        }
        return bestCategory;
    }
    analyzeSentiment(content) {
        const positive = ['good', 'great', 'excellent', 'happy', 'love', 'best', 'awesome', 'fantastic', 'wonderful', 'perfect'];
        const negative = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disappointing', 'sad', 'angry', 'frustrated'];
        const tokens = (0, embeddings_1.tokenize)(content.toLowerCase());
        const posCount = tokens.filter(t => positive.includes(t)).length;
        const negCount = tokens.filter(t => negative.includes(t)).length;
        const total = posCount + negCount;
        if (total === 0)
            return 0;
        return (posCount - negCount) / Math.max(total, 5);
    }
    assessImportance(content, entities, concepts) {
        let score = 0.5;
        // Length factor
        if (content.length > 100)
            score += 0.1;
        if (content.length > 300)
            score += 0.1;
        // Entity density
        score += Math.min(entities.length * 0.05, 0.15);
        // Concept richness
        score += Math.min(concepts.length * 0.02, 0.1);
        // Explicit importance markers
        if (/\b(important|critical|crucial|essential|key|main|primary)\b/i.test(content)) {
            score += 0.1;
        }
        return Math.min(score, 1.0);
    }
}
exports.SemanticLayerBuilder = SemanticLayerBuilder;
