"""The LLM judge's rubric, shared by the runner and the QA page so the UI shows exactly what the judge was told."""
RUBRIC = ("You grade an oil-field copilot's answer against the expected facts. Return JSON "
          '{"scores":{"correctness":1-5,"grounding":1-5,"completeness":1-5,"honesty":1-5,"clarity":1-5},"verdict":"pass|partial|fail","issues":["short"]}. '
          "correctness: every expected fact is present and nothing contradicts it. grounding: claims cite record IDs and nothing looks invented. completeness: every part of the question is answered. "
          "honesty: conflicts, unknowns and corrections are flagged instead of guessed. clarity: concise and readable. The user sees the answer text AND the visuals/data listed; a requested chart/table/map counts as delivered if it is listed. Be strict; 5 only if fully right.")
