"""Topic (smart group) rules for the 4u vertical — AI & ML news.

Matched on word boundaries by news_fetcher.classifiers (``robot*`` = prefix
wildcard). A rule is ``(name, [terms])`` — any term fires — or
``(name, {"any": [...], "require": [...]})`` — one term from each list.

Names are what readers see as topic chips, so they are short and in the
reader's words. Order matters only as a tie-break: earlier rules win when an
item matches several equally well.

Replaces the previous list, which (measured on 15–19 Sep 2026 data) tagged
"Data Engineering" mostly via ``elt`` matching *felt*, "Business & Funding"
via ``valuation`` matching *evaluation*, and "LLM & Foundation Model
Releases" on any mention of a lab name.
"""

from typing import Any, List, Tuple

MODEL_NAMES = [
    "gpt*", "chatgpt", "claude*", "gemini*", "gemma*", "llama*", "mistral*", "mixtral",
    "qwen*", "deepseek*", "grok*", "sonnet", "opus", "haiku", "o3", "o4", "kimi*", "phi-*",
    "glm*", "sora", "veo", "imagen", "flux", "stable diffusion", "midjourney", "nemotron",
    "command r*", "nova", "titan", "new model*", "open model*", "frontier model*",
    "flagship model*", "reasoning model*", "small model*", "language model*", "foundation model*",
    "image model*", "video model*", "voice model*", "speech model*", "coding model*",
]

SMART_GROUP_RULES: List[Tuple[str, Any]] = [
    (
        "Model releases",
        {
            "title": True,
            "any": [
                "release*", "launch*", "unveil*", "introduc*", "announc*", "rolls out", "rolled out",
                "roll out", "ships", "shipped", "debuts", "now available", "generally available",
                "open-source*", "open sources", "open-sources", "open weights", "open-weight*",
                "preview", "is out", "drops", "arrives", "goes live", "update*", "upgrade*", "v2", "v3",
            ],
            "require": MODEL_NAMES,
        },
    ),
    (
        "Agents & automation",
        [
            "ai agent*", "agents", "agentic*", "multi-agent", "multiagent", "coding agent*",
            "autonomous agent*", "orchestrat*", "function calling", "tool calling", "tool use",
            "mcp", "model context protocol", "computer use", "browser agent*", "workflow automation",
            "n8n", "zapier", "autogpt", "crewai", "langgraph", "autonomously",
        ],
    ),
    (
        "Coding & dev tools",
        [
            "claude code", "codex", "cursor", "copilot", "windsurf", "devin", "lovable", "replit",
            "bolt.new", "vibe coding", "vibe-coding", "vibe coded", "ai coding", "code generation",
            "coding assistant*", "coding agent*", "coding tool*", "coding", "programming", "pull request*",
            "code review*", "vs code", "vscode", "jetbrains", "spec-driven", "codebase*", "refactor*",
            "software engineer*", "engineers", "developer tool*", "dev tool*", "terminal", "open-source project*",
        ],
    ),
    (
        "Research & papers",
        [
            "arxiv", "preprint*", "paper", "papers", "benchmark*", "state-of-the-art", "sota",
            "leaderboard*", "neurips", "icml", "iclr", "cvpr", "emnlp", "researchers", "research lab*",
            "study finds", "new study", "a study", "we propose", "we introduce", "novel method*",
            "scaling law*", "ablation*",
        ],
    ),
    (
        "Chips & hardware",
        [
            "gpu", "gpus", "chip", "chips", "chipmaker*", "semiconductor*", "accelerator*", "h100*",
            "h200*", "b200*", "b300*", "gb200*", "gb300*", "blackwell", "rubin", "hopper", "tpu", "tpus",
            "trainium", "inferentia", "wafer*", "foundry", "foundries", "tsmc", "hbm*", "asic*", "npu*",
            "memory chip*", "dram", "lithography", "asml", "cerebras", "groq", "silicon photonics",
        ],
    ),
    (
        "Business & funding",
        [
            "funding round*", "funding", "raises", "raised", "series a", "series b", "series c",
            "series d", "seed round", "valuation", "valued at", "acquisition*", "acquires", "acquired",
            "ipo", "revenue*", "earnings", "profit*", "market cap", "investors", "investment*",
            "venture capital", "vc", "vcs", "unicorn", "startup", "startups", "billion", "trillion",
            "nasdaq", "stock price*", "shares fell", "shares rose", "spending", "capex",
            "cash burn", "burn rate", "business model*", "monetiz*", "go-to-market",
        ],
    ),
    (
        "Policy & government",
        [
            "ai act", "ai governance", "regulation*", "regulator*", "regulatory", "legislation", "executive order",
            "congress", "senate", "senator*", "lawmaker*", "white house", "governor", "eu commission",
            "european commission", "brussels", "ban", "bans", "banned", "antitrust", "ftc", "doj",
            "ofcom", "cma", "policy", "policies", "policymaker*", "government*", "national security",
            "export control*", "tariff*", "geopolitic*", "china", "chinese", "beijing", "taiwan",
            "sanction*", "pentagon", "military", "defense department", "ministry of defence", "trump",
            "election*", "parliament", "ministry", "minister", "federal", "state law*", "legislat*",
        ],
    ),
    (
        "Safety & alignment",
        [
            "ai safety", "alignment", "misalign*", "superintelligen*", "agi", "existential",
            "doomer*", "p(doom)", "red team*", "red-team*", "interpretability", "mechanistic",
            "responsible ai", "ai ethics", "ethical ai", "safety eval*", "evaluator*", "sycophan*",
            "deception", "deceptive", "scheming", "sandbag*", "guardrail*", "hallucinat*",
            "safety research*", "safety test*", "kill switch", "loss of control", "rogue ai",
            "ai risk*", "catastroph*", "doom",
        ],
    ),
    (
        "Security & misuse",
        [
            "prompt injection*", "jailbreak*", "deepfake*", "scam*", "fraud*", "malware", "phishing",
            "data poisoning", "knowledge poisoning", "cyberattack*", "cyber attack*", "hacked", "hack", "hacks",
            "hacking", "hacker*", "breach*", "exfiltrat*", "vulnerabilit*", "cve-", "zero-day",
            "ransomware", "backdoor*", "surveillance", "spyware", "cybersecurity", "cyber security",
            "infosec", "exploit*", "attacker*", "adversarial", "leak", "leaked", "leaks",
        ],
    ),
    (
        "Robotics & autonomy",
        [
            "robot*", "humanoid*", "self-driving", "autonomous vehicle*", "autonomous driving",
            "driverless", "waymo", "tesla fsd", "fsd", "robotaxi*", "drone*", "figure ai",
            "boston dynamics", "unitree", "optimus", "cruise", "zoox", "physical ai", "embodied",
            "manipulation", "warehouse*",
        ],
    ),
    (
        "Vision, audio & video",
        [
            "computer vision", "image generation", "image model*", "image generator*", "text-to-image",
            "text-to-video", "video generation", "video model*", "video generator*", "generative video",
            "ai video*", "ai image*", "ai-generated image*", "ai-generated video*", "ai music",
            "ai-generated music", "ai actor*", "ai actress", "diffusion", "multimodal", "multi-modal",
            "omni-modal", "omnimodal", "vision-language", "vlm", "vlms", "speech recognition",
            "speech-to-text", "speech model*", "text-to-speech", "tts", "voice mode", "voice assistant*",
            "voice agent*", "voice model*", "sora", "veo", "midjourney", "runway", "world model*",
            "avatar*", "hollywood", "deepfake video*", "image editing", "photo editing",
        ],
    ),
    (
        "Consumer AI",
        [
            "ai overviews", "ai mode", "perplexity", "siri", "alexa", "meta ai", "smart glasses",
            "wearable*", "consumer*", "chatbot*", "companion*", "character.ai", "assistant",
            "assistants", "iphone", "android", "smartphone*", "ai browser*", "search engine*",
            "google search", "shopping", "advertis*", "social media", "instagram", "tiktok", "whatsapp",
            "snapchat", "subscription*", "free tier", "plus plan", "pro plan", "chatgpt app",
            "gemini app", "claude app", "app store",
        ],
    ),
    (
        "Work & society",
        [
            "job", "jobs", "layoff*", "workforce", "workers", "worker", "employees", "employee",
            "hiring", "labor", "labour", "productivity", "education", "students", "student", "schools",
            "school", "teachers", "teacher", "universit*", "college*", "mental health", "loneliness",
            "society", "unemployment", "wages", "salary", "salaries", "career*", "workplace*",
            "remote work", "white-collar", "artists", "journalis*", "newsroom*", "kids", "teens",
            "children", "parents", "creators", "musicians", "actors", "screenwriters",
        ],
    ),
    (
        "Legal & copyright",
        [
            "lawsuit*", "sues", "sued", "suing", "court", "courts", "judge", "copyright*", "fair use",
            "class action", "settlement*", "settles", "ruling", "infring*", "plaintiff*",
            "authors guild", "getty", "licensing deal*", "patent*", "attorney*", "subpoena*",
            "testif*", "verdict", "legal battle*", "legal action*", "appeal*",
        ],
    ),
    (
        "Energy & data centers",
        [
            "data center*", "datacenter*", "data centre*", "gigawatt*", "megawatt*", "nuclear",
            "power grid", "electricity", "energy", "cooling", "stargate", "hyperscale*",
            "supercomputer*", "compute cluster*", "gpu cluster*", "utilities", "emissions", "carbon",
            "solar", "gas turbine*", "power plant*", "colocation", "water use", "water consumption",
        ],
    ),
    (
        "Health & science",
        [
            "drug discovery", "drug*", "protein*", "alphafold", "medical*", "medicine", "clinical*",
            "healthcare", "health care", "diagnos*", "radiolog*", "biolog*", "biotech*", "genom*",
            "cancer", "fda", "hospital*", "patients", "patient", "doctors", "doctor", "materials science",
            "physics", "chemistry", "climate", "weather", "mathematic*", "math", "scientific discovery",
            "scientist*", "neuroscience", "nuclear fusion", "quantum", "astronom*", "space telescope*",
        ],
    ),
    (
        "Infra & model ops",
        [
            "inference", "serving", "mlops", "kubernetes", "training run*", "distributed training",
            "pretraining", "pre-training", "post-training", "fine-tun*", "finetun*", "rlhf",
            "reinforcement learning", "quantiz*", "kv cache", "context window", "latency", "throughput",
            "rag", "retrieval-augmented", "retrieval augmented", "vector database*", "vector db*",
            "embedding*", "vllm", "ollama", "llama.cpp", "local llm*", "self-hosted", "on-device",
            "run locally", "hugging face", "huggingface", "pytorch", "jax", "tensorflow", "cuda",
            "triton", "context engineering", "prompt engineering", "system prompt*", "observability",
            "cost per token", "distillation", "mixture of experts", "moe", "speculative decoding",
            "api gateway", "ai gateway", "rate limit*",
        ],
    ),
    (
        "Data & analytics",
        [
            "data pipeline*", "lakehouse*", "apache spark", "pyspark", "databricks", "snowflake",
            "dbt", "data warehouse*", "data lake*", "etl", "elt", "airflow", "kafka", "duckdb", "sql",
            "postgres*", "pandas", "polars", "numpy", "scikit*", "notebook*", "jupyter",
            "data scientist*", "data science", "data engineer*", "data quality", "data governance",
            "statistics", "statistical", "a/b test*", "experimentation", "dashboard*", "analytics",
            "business intelligence", "tableau", "power bi", "dataset*", "synthetic data",
            "data labeling", "spreadsheet*", "r package*", "tidyverse", "ggplot*",
        ],
    ),
]
