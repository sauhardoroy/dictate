#pragma once
#include <string>
#include <vector>
#include <unordered_set>
#include <algorithm>
#include <sstream>
#include <regex>

namespace Dictate {
namespace Punctuation {

inline const std::unordered_set<std::string> INCOMPLETE_TRAILING_WORDS = {
    // Conjunctions
    "and", "or", "but", "so", "because", "although", "though", "while", "if", "when",
    "that", "as", "since", "unless", "until", "whereas", "whether", "plus", "also",
    // Prepositions
    "to", "for", "in", "on", "at", "with", "about", "by", "from", "into", "through",
    "of", "towards", "toward", "over", "under", "between", "after", "before", "during",
    "without", "against", "among", "per", "via",
    // Articles & Determiners
    "the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her",
    "our", "their", "its", "some", "any", "every", "each", "both", "either", "neither",
    "such", "another", "which", "whose", "what",
    // Modals & Auxiliary Verbs (hanging sentence)
    "is", "are", "was", "were", "be", "been", "being",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "have", "has", "had", "do", "does", "did", "going", "trying", "wanting",
    // Common speech thinking fillers
    "um", "uh", "er", "ah", "like", "you", "know", "mean", "basically", "actually"
};

inline bool is_incomplete_thought(const std::string& text) {
    if (text.empty()) return false;

    // Convert to lowercase and strip punctuation
    std::string clean;
    clean.reserve(text.size());
    for (char c : text) {
        if (std::isalnum(static_cast<unsigned char>(c)) || std::isspace(static_cast<unsigned char>(c))) {
            clean += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        } else {
            clean += ' ';
        }
    }

    std::istringstream iss(clean);
    std::vector<std::string> tokens;
    std::string word;
    while (iss >> word) {
        tokens.push_back(word);
    }

    if (tokens.empty()) return false;

    const std::string& last_word = tokens.back();
    if (INCOMPLETE_TRAILING_WORDS.find(last_word) != INCOMPLETE_TRAILING_WORDS.end()) {
        return true;
    }

    if (tokens.size() >= 2) {
        const std::string& prev = tokens[tokens.size() - 2];
        if ((prev == "going" && last_word == "to") ||
            (prev == "want" && last_word == "to") ||
            (prev == "need" && last_word == "to") ||
            (prev == "have" && last_word == "to") ||
            (prev == "trying" && last_word == "to") ||
            (prev == "kind" && last_word == "of") ||
            (prev == "sort" && last_word == "of")) {
            return true;
        }
    }

    if (last_word == "more" || last_word == "less" || last_word == "greater" ||
        last_word == "fewer" || last_word == "better" || last_word == "worse") {
        return true;
    }

    return false;
}

inline double get_adaptive_silence_duration(const std::string& partial_transcript, double base_silence_seconds = 1.4) {
    if (partial_transcript.empty()) return base_silence_seconds;

    if (is_incomplete_thought(partial_transcript)) {
        return std::max(2.5, base_silence_seconds * 2.2);
    }
    return base_silence_seconds;
}

} // namespace Punctuation
} // namespace Dictate
