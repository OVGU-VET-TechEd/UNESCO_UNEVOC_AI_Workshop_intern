Check the TVET policy summary below against the style guide in your instructions.

Return ONLY a JSON object with exactly these keys:
{
  "neutral": true or false,
  "within_limit": true or false,
  "issues": ["short description of each problem, empty list if none"],
  "suggested_revision": "corrected summary of at most {{MAX_WORDS}} words, or an empty string if no change is needed"
}

Word count measured by the harness: {{WORD_COUNT}} (limit {{MAX_WORDS}}).

<summary>
{{TEXT}}
</summary>
