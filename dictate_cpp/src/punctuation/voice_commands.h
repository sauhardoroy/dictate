#pragma once
#include <string>
#include <regex>
#include <vector>

namespace Dictate {
namespace Punctuation {

struct VoiceCommand {
    std::regex pattern;
    std::string replacement;
};

inline std::string apply_voice_commands(const std::string& text) {
    if (text.empty()) return "";

    static const std::vector<VoiceCommand> commands = {
        { std::regex("\\b(new line|newline)\\b", std::regex_constants::icase), "\n" },
        { std::regex("\\b(new paragraph|next paragraph)\\b", std::regex_constants::icase), "\n\n" },
        { std::regex("\\b(period|full stop)\\b", std::regex_constants::icase), "." },
        { std::regex("\\b(comma)\\b", std::regex_constants::icase), "," },
        { std::regex("\\b(question mark)\\b", std::regex_constants::icase), "?" },
        { std::regex("\\b(exclamation mark|exclamation point)\\b", std::regex_constants::icase), "!" },
        { std::regex("\\b(colon)\\b", std::regex_constants::icase), ":" },
        { std::regex("\\b(semicolon|semi colon)\\b", std::regex_constants::icase), ";" },
        { std::regex("\\b(open quote|open quotation)\\b", std::regex_constants::icase), " \"" },
        { std::regex("\\b(close quote|close quotation)\\b", std::regex_constants::icase), "\" " },
        { std::regex("\\b(open parenthesis|open paren)\\b", std::regex_constants::icase), " (" },
        { std::regex("\\b(close parenthesis|close paren)\\b", std::regex_constants::icase), ") " },
        { std::regex("\\b(dash|hyphen)\\b", std::regex_constants::icase), "-" },
        { std::regex("\\b(ellipsis|dot dot dot)\\b", std::regex_constants::icase), "..." }
    };

    std::string result = text;
    for (const auto& cmd : commands) {
        result = std::regex_replace(result, cmd.pattern, cmd.replacement);
    }

    // Clean whitespace around punctuation
    result = std::regex_replace(result, std::regex("\\s+([,.!?:;])"), "$1");
    result = std::regex_replace(result, std::regex("\\(\\s+"), "(");
    result = std::regex_replace(result, std::regex("\\s+\\)"), ")");
    result = std::regex_replace(result, std::regex("\\s+"), " ");

    // Trim
    auto start = result.find_first_not_of(" \t\n\r");
    auto end = result.find_last_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    result = result.substr(start, end - start + 1);

    // Capitalize first letter
    if (!result.empty() && std::isalpha(static_cast<unsigned char>(result[0]))) {
        result[0] = static_cast<char>(std::toupper(static_cast<unsigned char>(result[0])));
    }

    return result;
}

} // namespace Punctuation
} // namespace Dictate
