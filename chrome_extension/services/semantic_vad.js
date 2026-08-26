/**
 * Semantic Thought-Completion Evaluator for Chrome Extension Dictation
 */

const INCOMPLETE_TRAILING_WORDS = new Set([
  "and", "or", "but", "so", "because", "although", "though", "while", "if", "when",
  "that", "as", "since", "unless", "until", "to", "for", "in", "on", "at", "with",
  "about", "by", "from", "into", "through", "of", "towards", "the", "a", "an", "this",
  "that", "these", "those", "my", "your", "his", "her", "our", "their", "is", "are",
  "was", "were", "will", "would", "shall", "should", "can", "could", "have", "has",
  "had", "um", "uh", "er", "ah", "like", "you", "know"
]);

function isSpeechThoughtIncomplete(text) {
  if (!text) return false;
  const clean = text.toLowerCase().replace(/[^\w\s]/g, " ").trim();
  const tokens = clean.split(/\s+/);
  if (tokens.length === 0) return false;
  const last = tokens[tokens.length - 1];
  return INCOMPLETE_TRAILING_WORDS.has(last);
}

if (typeof module !== "undefined") {
  module.exports = { isSpeechThoughtIncomplete };
}
