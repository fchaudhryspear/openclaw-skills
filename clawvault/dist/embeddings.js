"use strict";
/**
 * Embedding Utilities
 * Generates vector representations for semantic search
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateEmbedding = generateEmbedding;
exports.cosineSimilarity = cosineSimilarity;
exports.tokenize = tokenize;
exports.removeStopwords = removeStopwords;
exports.calculateRecencyBoost = calculateRecencyBoost;
exports.extractKeywords = extractKeywords;
const crypto = __importStar(require("crypto"));
// Simple embedding generation using word hashing (for demo purposes)
// In production, use a real embedding model like OpenAI, HuggingFace, etc.
const EMBEDDING_DIMENSION = 128;
function generateEmbedding(text) {
    const normalized = text.toLowerCase().trim();
    const embedding = new Array(EMBEDDING_DIMENSION).fill(0);
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
function cosineSimilarity(a, b) {
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
    if (normA === 0 || normB === 0)
        return 0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}
function tokenize(text) {
    return text
        .toLowerCase()
        .replace(/[^\w\s]/g, ' ')
        .split(/\s+/)
        .filter(t => t.length > 1);
}
function removeStopwords(tokens) {
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
function generateNgrams(words, minN, maxN) {
    const ngrams = [];
    for (let n = minN; n <= maxN && n <= words.length; n++) {
        for (let i = 0; i <= words.length - n; i++) {
            ngrams.push(words.slice(i, i + n).join('_'));
        }
    }
    return ngrams;
}
function hashString(str) {
    return crypto.createHash('md5').update(str).digest().readUInt32LE(0);
}
function normalizeVector(vec) {
    const norm = Math.sqrt(vec.reduce((sum, val) => sum + val * val, 0));
    if (norm === 0)
        return vec;
    return vec.map(val => val / norm);
}
function calculateRecencyBoost(timestamp, halfLife = 86400000) {
    const age = Date.now() - timestamp;
    return Math.exp(-age / halfLife);
}
function extractKeywords(text) {
    const tokens = tokenize(text);
    return removeStopwords(tokens);
}
//# sourceMappingURL=embeddings.js.map