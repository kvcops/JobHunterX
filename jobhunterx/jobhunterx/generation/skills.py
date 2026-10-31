"""Group the candidate's own skills into categories for documents (no fixed category list)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot, norm_term
from jobhunterx.generation.content import SkillGroup
from jobhunterx.intelligence.llm_structured import call_structured

VERSION = "skillgroups-v2"


class _Groups(BaseModel):
    groups: list[SkillGroup] = Field(default_factory=list)


_SYSTEM = """Group a candidate's skills into 3-6 clear resume categories that suit this candidate's field.
Use ONLY the skill names given, spelled exactly as given; every skill must appear in exactly one group.
A name that is itself a category heading rather than a skill (e.g. "Operations & Reliability", "Cloud & Managed
Services") is not a skill: use it as a category name if it fits, never as an item."""

# When no model answers (or its answer is cut off), skills are still grouped — never one long "Skills" line.
# Checked in order; a skill goes to the first bucket one of whose terms it contains (word match).
_FALLBACK = [
    ("Languages", ("python", "java", "javascript", "typescript", "c++", "c#", "golang", "go", "rust", "kotlin", "swift",
                   "scala", "ruby", "php", "bash", "shell", "powershell", "perl", "r", "sql", "html", "css", "matlab")),
    ("AI / ML & Data", ("machine learning", "deep learning", "ml", "ai", "llm", "llms", "rag", "nlp", "pytorch",
                        "tensorflow", "keras", "scikit-learn", "sklearn", "langchain", "hugging face", "transformers",
                        "pandas", "numpy", "spark", "hadoop", "jupyter", "data", "analytics", "tableau", "power bi",
                        "computer vision", "opencv", "genai", "generative", "faiss", "vector")),
    ("Cloud & DevOps", ("aws", "azure", "gcp", "google cloud", "cloud", "docker", "kubernetes", "k8s", "terraform",
                        "ansible", "jenkins", "ci/cd", "cicd", "github actions", "devops", "helm", "openshift",
                        "cloudwatch", "ec2", "s3", "iam", "vpc", "lambda", "serverless", "puppet", "chef")),
    ("HPC & Systems", ("hpc", "slurm", "lsf", "sge", "grid engine", "cluster", "infiniband", "nvlink", "gpu", "cuda",
                       "lustre", "gpfs", "spack", "easybuild", "lmod", "environment modules", "nfs", "bcm",
                       "parallel", "mpi", "linux", "rhel", "centos", "ubuntu", "solaris", "unix", "kernel",
                       "virtualization", "vmware", "storage", "patching")),
    ("Networking & Security", ("network", "networking", "vpn", "vpns", "firewall", "firewalls", "tcp/ip", "dns",
                               "security", "compliance", "iam", "ssl", "tls", "interconnects")),
    ("Web & Backend", ("react", "angular", "vue", "node", "node.js", "express", "django", "flask", "fastapi",
                       "spring", "rest", "graphql", "api", "apis", "microservices", "next.js")),
    ("Databases", ("postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite", "oracle", "cassandra",
                   "dynamodb", "elasticsearch", "database", "databases")),
    ("Tools & Practices", ("git", "github", "gitlab", "jira", "vs code", "splunk", "grafana", "prometheus",
                           "monitoring", "incident", "rca", "root cause", "agile", "scrum", "testing", "automation",
                           "disaster recovery", "performance", "troubleshooting", "sev", "reliability")),
]
_HEADING_WORDS = ("services", "platforms", "ecosystem", "architectures", "operations")


def _words(text: str) -> set[str]:
    import re
    return set(re.findall(r"[a-z0-9+#./]+", text.lower()))


def _fallback_groups(names: list[str]) -> list[SkillGroup]:
    buckets: dict[str, list[str]] = {}
    for n in names:
        low, w = n.lower(), _words(n)
        cat = next((c for c, terms in _FALLBACK
                    if any((t in w) if " " not in t else (t in low) for t in terms)), "Other")
        buckets.setdefault(cat, []).append(n)
    order = [c for c, _ in _FALLBACK] + ["Other"]
    groups = [SkillGroup(category=c, items=buckets[c]) for c in order if buckets.get(c)]
    # a lone leftover or two read better folded into the biggest group than as their own "Other" line
    if len(groups) > 1 and groups[-1].category == "Other" and len(groups[-1].items) <= 2:
        extra = groups.pop().items
        max(groups, key=lambda g: len(g.items)).items.extend(extra)
    return groups


def _drop_bracketed_repeats(names: list[str]) -> list[str]:
    """'Lmod' is already in 'Environment Modules (Lmod, EasyBuild, Spack)': list it once."""
    import re
    inside = {norm_term(x) for n in names for grp in re.findall(r"\(([^)]*)\)", n) for x in re.split(r"[,/;]", grp) if x.strip()}
    return [n for n in names if "(" in n or norm_term(n) not in inside]


def _is_heading(name: str) -> bool:
    """'Operations & Reliability', 'Cloud & Managed Services': a section heading copied in as a skill."""
    low = name.lower()
    return ("&" in name or " and " in low) and low.split()[-1].strip(")") in _HEADING_WORDS + ("reliability",)


async def group_skills(profile: CandidateProfile, snapshot: CandidateSnapshot, *, use_llm: bool = True) -> tuple[list[SkillGroup], str]:
    names = [s.name for s in snapshot.skills] or list(profile.skills)
    seen: set[str] = set()
    names = [n for n in names if n and not (norm_term(n) in seen or seen.add(norm_term(n)))]
    names = [n for n in names if not _is_heading(n)] or names
    names = _drop_bracketed_repeats(names)
    if not names:
        return [], ""
    groups, model = (None, "")
    if use_llm:
        groups, model = await call_structured(
            task="skill_groups", version=VERSION, model=_Groups, system=_SYSTEM,
            user="Skills: " + " | ".join(names), chain="fast", max_tokens=2400,
            cache_parts=(profile.content_hash(), "|".join(names)),
        )
    allowed = {norm_term(n): n for n in names}
    out, used = [], set()
    for g in (groups.groups if groups else []):
        items = []
        for it in g.items:
            k = norm_term(it)
            if k in allowed and k not in used:
                used.add(k)
                items.append(allowed[k])
        if items and g.category.strip():
            out.append(SkillGroup(category=g.category.strip()[:40], items=items))
    rest = [n for k, n in allowed.items() if k not in used]
    if not out:
        return _fallback_groups(rest), ""
    if rest:
        out.append(SkillGroup(category="Other", items=rest))
    return out, model if groups else ""
