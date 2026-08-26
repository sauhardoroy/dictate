/**
 * Voice Commands and Punctuation Formatting Service
 * Automatically converts spoken punctuation commands into symbols.
 */

const VOICE_COMMAND_MAP = [
  { pattern: /\b(new line|newline)\b/gi, replacement: "\n" },
  { pattern: /\b(new paragraph|next paragraph)\b/gi, replacement: "\n\n" },
  { pattern: /\b(period|full stop)\b/gi, replacement: "." },
  { pattern: /\b(comma)\b/gi, replacement: "," },
  { pattern: /\b(question mark)\b/gi, replacement: "?" },
  { pattern: /\b(exclamation mark|exclamation point)\b/gi, replacement: "!" },
  { pattern: /\b(colon)\b/gi, replacement: ":" },
  { pattern: /\b(semicolon|semi colon)\b/gi, replacement: ";" },
  { pattern: /\b(open quote|open quotation)\b/gi, replacement: ' "' },
  { pattern: /\b(close quote|close quotation)\b/gi, replacement: '" ' },
  { pattern: /\b(open parenthesis|open paren)\b/gi, replacement: " (" },
  { pattern: /\b(close parenthesis|close paren)\b/gi, replacement: ") " },
  { pattern: /\b(dash|hyphen)\b/gi, replacement: "-" },
  { pattern: /\b(ellipsis|dot dot dot)\b/gi, replacement: "..." }
];

function applyVoiceFormatting(text) {
  if (!text) return "";
  let formatted = text;

  for (const cmd of VOICE_COMMAND_MAP) {
    formatted = formatted.replace(cmd.pattern, cmd.replacement);
  }

  // Clean up whitespace around punctuation marks
  formatted = formatted.replace(/\s+([,.!?:;])/g, "$1");
  formatted = formatted.replace(/\(\s+/g, "(");
  formatted = formatted.replace(/\s+\)/g, ")");
  formatted = formatted.replace(/\s+/g, " ").trim();

  // Capitalize first letter
  if (formatted.length > 0) {
    formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
  }

  return formatted;
}

if (typeof module !== "undefined") {
  module.exports = { applyVoiceFormatting };
}
