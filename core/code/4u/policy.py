"""Quality policy for the 4u (AI & ML) vertical.

Measured on four days of live data (15–19 Sep 2026), 38% of "headline"
items from the general tech/business feeds had no AI term anywhere in title
or summary. The relevance gate below only applies to those general source
classes; AI-specific feeds are exempt by their own title.
"""

import re

from news_fetcher.quality import Policy

TOPIC_TERMS = re.compile(
    r"(?<![a-z0-9])(?:"
    r"ai|a\.i\.|artificial intelligence|machine learning|deep learning|"
    r"llms?|gpt(?:-?\d\S*)?|chatgpt|openai|anthropic|claude|gemini|gemma|copilot|"
    r"deepmind|deepseek|mistral|llama|qwen|grok|xai|perplexity|midjourney|"
    r"hugging ?face|cursor|windsurf|codex|sora|veo|"
    r"neural|language models?|foundation models?|frontier models?|"
    r"agents?|agentic|chatbots?|robots?|robotics?|robotaxis?|humanoids?|self-driving|autonomous|"
    r"nvidia|gpus?|tpus?|ai chips?|"
    r"transformers?|generative|diffusion|inference|training data|fine-?tun\w*|"
    r"superintelligence|agi|alignment|deepfakes?|prompt injection"
    r")(?![a-z0-9])",
    re.IGNORECASE,
)

POLICY = Policy(
    # "official-labs-research" holds arXiv (exempt below) but also general
    # science magazines, which post far more than AI.
    gated_source_types={"media-tech-analysis", "general-news", "official-labs-research"},
    topic_terms=TOPIC_TERMS,
    exempt_source_pattern=re.compile(
        r"\b(?:ai|artificial intelligence|machine learning|deep learning|llm|data science|arxiv)\b",
        re.IGNORECASE,
    ),
    drop_arxiv_announce_types={"replace", "cross", "replace-cross"},
    # The base list is a security vocabulary (zero-day, ransomware…); it
    # flagged 29% of AI headlines as "curated" for no reader-visible reason.
    curated_keywords=[],
    aggregator_pattern=re.compile(
        r"techmeme|hacker news|product hunt|newsletter|\[ainews\]|the rundown|"
        r"news on artificial intelligence and machine learning",
        re.IGNORECASE,
    ),
    max_smart_groups=3,
    summary_mode="fallback",
    story_window_hours=72,
)
